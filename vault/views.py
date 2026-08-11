import uuid
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from .forms import UploadFileForm
from django.core.files.storage import storages
from application.graph.graph import execute_query

files_storage = storages["files_storage"]

@login_required(login_url='login')
def vault_dashboard(request):
    return get_fileorFolders(request)

def get_file_type(filename):
    if not filename:
        return 'document'
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp']:
        return 'image'
    elif ext in ['mp4', 'mkv', 'avi', 'mov', 'webm']:
        return 'video'
    elif ext in ['mp3', 'wav', 'aac', 'flac', 'ogg']:
        return 'audio'
    elif ext in ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'iso']:
        return 'archive'
    elif ext in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'md']:
        return 'document'
    return 'document'

def format_size_mb(size_in_bytes):
    if not size_in_bytes:
        return "0 MB"
    try:
        bytes_val = float(size_in_bytes)
        mb_val = bytes_val / (1024 * 1024)
        if mb_val < 0.01:
            return f"{mb_val:.3f} MB"
        return f"{mb_val:.2f} MB"
    except (ValueError, TypeError):
        return "N/A"

def format_date(timestamp):
    if not timestamp:
        return "N/A"
    try:
        ts_str = str(timestamp).replace('Z', '')
        datetime_obj = datetime.fromisoformat(ts_str)
        return datetime_obj.strftime("%b %d, %Y, %I:%M %p")
    except Exception:
        try:
            clean_ts = str(timestamp).split('.')[0]
            datetime_obj = datetime.strptime(clean_ts, "%Y-%m-%dT%H:%M:%S")
            return datetime_obj.strftime("%b %d, %Y, %I:%M %p")
        except Exception:
            return str(timestamp)

def get_breadcrumbs(folder_id, username):
    if not folder_id or folder_id == 0:
        return []
    
    breadcrumbs = []
    curr_id = folder_id
    visited = set()
    while curr_id and curr_id != 0 and curr_id not in visited:
        visited.add(curr_id)
        query = """
        MATCH (f:Folder {id: $id})-[:OWNED_BY]->(u:User {username: $username})
        RETURN f
        """
        res = execute_query(query, id=curr_id, username=username)
        if res and hasattr(res, 'records') and len(res.records) > 0:
            f_node = dict(res.records[0].get('f'))
            breadcrumbs.insert(0, {'id': f_node.get('id'), 'name': f_node.get('name')})
            parent_id = f_node.get('parent_id')
            if parent_id is not None and parent_id != 0 and str(parent_id) != '0':
                try:
                    curr_id = int(parent_id)
                except (ValueError, TypeError):
                    break
            else:
                rel_query = """
                MATCH (parent:Folder)-[:PARENT_OF]->(f:Folder {id: $id})
                RETURN parent.id AS parent_id
                """
                rel_res = execute_query(rel_query, id=curr_id)
                if rel_res and hasattr(rel_res, 'records') and len(rel_res.records) > 0:
                    curr_id = rel_res.records[0].get('parent_id')
                else:
                    break
        else:
            break
    return breadcrumbs

@login_required(login_url='login')
def get_fileorFolders(request):
    form = UploadFileForm()

    folder_id_param = request.GET.get('folder_id') or request.GET.get('folder')
    try:
        folder_id = int(folder_id_param) if folder_id_param else 0
    except (ValueError, TypeError):
        folder_id = 0

    category = request.GET.get('category', '').lower()
    view_mode = request.GET.get('view', '').lower()

    CATEGORY_PATTERNS = {
        'documents': r'(?i).*\.(pdf|doc|docx|txt|rtf|odt|xls|xlsx|ppt|pptx|csv|md)$',
        'media': r'(?i).*\.(jpg|jpeg|png|gif|bmp|svg|webp|mp4|mkv|avi|mov|mp3|wav|aac|flac)$',
        'archives': r'(?i).*\.(zip|rar|7z|tar|gz|bz2|xz|iso)$',
    }

    folder_query = None

    if view_mode == 'shared':
        # Shared view: fetch files shared with the current user
        file_query = """
        MATCH (f:File)-[r:SHARED_WITH]->(u:User {username: $username})
        RETURN f, r.permission AS permission
        """
    elif category in CATEGORY_PATTERNS:
        # Category view: filter files across entire vault by extension pattern
        file_query = """
        MATCH (f:File)-[:OWNED_BY]->(u:User {username: $username})
        WHERE f.name =~ $pattern
        RETURN f
        """
    elif folder_id != 0:
        # Specific sub-folder view: fetch child files and sub-folders
        file_query = """
        MATCH (parent:Folder {id: $folder_id})-[:PARENT_OF]->(f:File)-[:OWNED_BY]->(u:User {username: $username})
        RETURN f
        """
        folder_query = """
        MATCH (parent:Folder {id: $folder_id})-[:PARENT_OF]->(f:Folder)-[:OWNED_BY]->(u:User {username: $username})
        RETURN f
        """
    else:
        # Root view: fetch files and folders having parent_id as 0 or NULL
        file_query = """
        MATCH (f:File)-[:OWNED_BY]->(u:User {username: $username})
        WHERE f.parent_id IS NULL OR f.parent_id = 0 OR f.parent_id = '0'
        RETURN f
        """
        folder_query = """
        MATCH (f:Folder)-[:OWNED_BY]->(u:User {username: $username})
        WHERE f.parent_id IS NULL OR f.parent_id = 0 OR f.parent_id = '0'
        RETURN f
        """

    files = []
    folders = []
    total_bytes = 0

    try:
        if category in CATEGORY_PATTERNS:
            f_result = execute_query(file_query, username=request.user.username, pattern=CATEGORY_PATTERNS[category])
        else:
            f_result = execute_query(file_query, username=request.user.username, folder_id=folder_id)

        if f_result and hasattr(f_result, 'records'):
            for record in f_result.records:
                file_node = record.get('f')
                if file_node:
                    file_dict = dict(file_node)
                    file_dict['file_type'] = get_file_type(file_dict.get('name', ''))
                    file_dict['formatted_size'] = format_size_mb(file_dict.get('size'))
                    file_dict['formated_date'] = format_date(file_dict.get('createdAt'))
                    if view_mode == 'shared':
                        file_dict['permission'] = record.get('permission')
                        file_dict['is_shared'] = True
                    try:
                        total_bytes += float(file_dict.get('size', 0))
                    except (ValueError, TypeError):
                        pass
                    files.append(file_dict)

        if folder_query:
            folder_result = execute_query(folder_query, username=request.user.username, folder_id=folder_id)
            if folder_result and hasattr(folder_result, 'records'):
                for record in folder_result.records:
                    folder_node = record.get('f')
                    if folder_node:
                        folders.append(dict(folder_node))
    except Exception as e:
        print(f"CognoDB node & relationship retrieval notice: {e}")
    
    total_storage_mb = format_size_mb(total_bytes)
    breadcrumbs = get_breadcrumbs(folder_id, request.user.username) if folder_id != 0 else []

    print(f"DEBUG ROOT FETCH - username: {request.user.username}, folder_id: {folder_id}, category: {category}, view_mode: {view_mode}")
    print(f"DEBUG ROOT FILES COUNT: {len(files)}, FILES: {files}")
    print(f"DEBUG ROOT FOLDERS COUNT: {len(folders)}, FOLDERS: {folders}")

    return render(request, 'homepage.html', {
        'form': form,
        'files': files,
        'folders': folders,
        'current_folder_id': folder_id,
        'current_category': category,
        'view_mode': view_mode,
        'total_storage_mb': total_storage_mb,
        'breadcrumbs': breadcrumbs,
    })

@login_required(login_url='login')
def vault_upload(request):
    folder_id_raw = request.POST.get('folder_id')
    print(folder_id_raw)
    try:
        folder_id = int(folder_id_raw) if folder_id_raw else 0
    except (ValueError, TypeError):
        folder_id = 0
    print(folder_id)
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            saved_name = files_storage.save(file.name, file)
            file_url = files_storage.url(saved_name)
            file_id = int(uuid.uuid4().int & 0x7fffffff)
            created_at = datetime.now().isoformat()

            query = """
            MERGE (u:User {username: $username})
            CREATE (f:File {
                id: $id,
                name: $name,
                url: $url,
                size: $size,
                createdAt: $createdAt,
                parent_id: $parent_id
            })
            CREATE (f)-[r:OWNED_BY {
                type: $type,
                since: $since
            }]->(u)
            RETURN f, r
            """
            try:
                execute_query(
                    query,
                    id=file_id,
                    name=file.name,
                    url=file_url,
                    size=file.size,
                    createdAt=created_at,
                    parent_id=folder_id,
                    username=request.user.username,
                    type='File',
                    since=created_at
                )

                if folder_id != 0:
                    parent_query = """
                    MATCH (parent:Folder), (child:File {id: $child_id})
                    WHERE parent.id = $parent_id OR parent.id = toString($parent_id) OR parent.id = toInteger($parent_id)
                    CREATE (parent)-[r:PARENT_OF {since: $since}]->(child)
                    RETURN parent, r, child
                    """
                    execute_query(parent_query, parent_id=folder_id, child_id=file_id, since=created_at)
                    parentquery = """
                        MATCH (u:User {username: $username})<-[:OWNED_BY]-(f:File {id: $id})
                        SET f.parent_id= $parent_id
                        RETURN f                    
                        """
                    execute_query(parentquery, username=request.user.username, id=file_id, parent_id=folder_id)
                    
            except Exception as e:
                print(f"CognoDB node & relationship creation notice: {e}")

            messages.success(request, f"File '{file.name}' uploaded successfully!")
        else:
            messages.error(request, "Error uploading file. Please choose a valid file.")

    redirect_url = f"/?folder_id={folder_id}" if folder_id != 0 else "/"
    return redirect(redirect_url)


@login_required(login_url='login')
def delete_file(request):
    folder_id_raw = request.POST.get('folder_id')
    try:
        folder_id = int(folder_id_raw) if folder_id_raw else 0
    except (ValueError, TypeError):
        folder_id = 0

    if request.method == 'POST':
        file_id = request.POST.get('file_id')
        if file_id:
            try:
                # 1. Fetch file node to retrieve filename for storage deletion
                fetch_query = """
                MATCH (f:File {id: $id})
                WHERE (f)-[:OWNED_BY]->(:User {username: $username}) OR (f)-[:SHARED_WITH {permission: 'delete'}]->(:User {username: $username})
                RETURN f
                """
                fetch_res = execute_query(fetch_query, id=int(file_id), username=request.user.username)
                
                file_name = None
                if fetch_res and hasattr(fetch_res, 'records') and len(fetch_res.records) > 0:
                    f_node = dict(fetch_res.records[0].get('f'))
                    file_name = f_node.get('name')
                
                # 2. Delete file from Cloudflare R2 storage bucket
                if file_name:
                    try:
                        if files_storage.exists(file_name):
                            files_storage.delete(file_name)
                    except Exception as storage_err:
                        print(f"Error deleting file from storage: {storage_err}")

                # 3. DETACH DELETE the node and relationships in CognoDB with explicit count return
                delete_query = """
                MATCH (f:File {id: $id})
                WHERE (f)-[:OWNED_BY]->(:User {username: $username}) OR (f)-[:SHARED_WITH {permission: 'delete'}]->(:User {username: $username})
                DETACH DELETE f
                RETURN count(f) AS deleted_count
                """
                execute_query(delete_query, id=int(file_id), username=request.user.username)
                messages.success(request, "File deleted successfully!")
            except Exception as e:
                print(f"CognoDB node & relationship deletion notice: {e}")
                messages.error(request, "Error deleting file.")
        else:
            messages.error(request, "Invalid file ID.")

    redirect_url = f"/?folder_id={folder_id}" if folder_id != 0 else "/"
    return redirect(redirect_url)


@login_required(login_url='login')
def search_files(request):
    query = request.GET.get('query', '')
    
    if query:
        search_files_query = """
        MATCH (f:File)-[:OWNED_BY]->(u:User {username: $username})
        WHERE toLower(f.name) CONTAINS toLower($search_term)
        RETURN f
        """
        
        search_folders_query = """
        MATCH (f:Folder)-[:OWNED_BY]->(u:User {username: $username})
        WHERE toLower(f.name) CONTAINS toLower($search_term)
        RETURN f
        """
        
        files = []
        folders = []
        try:
            # Fetch files
            result_files = execute_query(search_files_query, username=request.user.username, search_term=query)
            if result_files and hasattr(result_files, 'records'):
                for record in result_files.records:
                    file_node = record.get('f')
                    if file_node:
                        file_dict = dict(file_node)
                        file_dict['file_type'] = get_file_type(file_dict.get('name', ''))
                        file_dict['formatted_size'] = format_size_mb(file_dict.get('size'))
                        file_dict['formated_date'] = format_date(file_dict.get('createdAt'))
                        files.append(file_dict)
                        
            # Fetch folders
            result_folders = execute_query(search_folders_query, username=request.user.username, search_term=query)
            if result_folders and hasattr(result_folders, 'records'):
                for record in result_folders.records:
                    folder_node = record.get('f')
                    if folder_node:
                        folders.append(dict(folder_node))
                        
        except Exception as e:
            print(f"CognoDB search notice: {e}")
    else:
        files = []
        folders = []
    
    context = {
        'files': files,
        'folders': folders,
        'search_query': query,
    }
    return render(request, 'homepage.html', context)


@login_required(login_url='login')
def create_folder(request):
    folder_id_raw = request.POST.get('folder_id')
    try:
        parent_folder_id = int(folder_id_raw) if folder_id_raw else 0
    except (ValueError, TypeError):
        parent_folder_id = 0

    if request.method == 'POST':
        folder_name = request.POST.get('folder_name')
        if folder_name:
            new_folder_id = int(uuid.uuid4().int & 0x7fffffff)
            created_at = datetime.now().isoformat()

            query = """
            MERGE (u:User {username: $username})
            CREATE (f:Folder {
                id: $id,
                name: $name,
                createdAt: $createdAt,
                parent_id: $parent_id
            })
            CREATE (f)-[r:OWNED_BY {
                type: $type,
                since: $since
            }]->(u)
            RETURN f, r
            """
            try:
                execute_query(
                    query,
                    id=new_folder_id,
                    name=folder_name,
                    createdAt=created_at,
                    parent_id=parent_folder_id,
                    username=request.user.username,
                    type='Folder',
                    since=created_at
                )

                if parent_folder_id != 0:
                    parent_query = """
                    MATCH (parent:Folder), (child:Folder {id: $child_id})
                    WHERE parent.id = $parent_id OR parent.id = toString($parent_id) OR parent.id = toInteger($parent_id)
                    CREATE (parent)-[r:PARENT_OF {since: $since}]->(child)
                    RETURN parent, r, child
                    """
                    execute_query(parent_query, parent_id=parent_folder_id, child_id=new_folder_id, since=created_at)
                    parentquery = """
                        MATCH (u:User {username: $username})<-[:OWNED_BY]-(f:Folder {id: $id})
                        SET f.parent_id= $parent_id
                        RETURN f                    
                        """
                    execute_query(parentquery, username=request.user.username, id=new_folder_id, parent_id=parent_folder_id)

                messages.success(request, f"Folder '{folder_name}' created successfully!")
            except Exception as e:
                print(f"CognoDB node & relationship creation notice: {e}")
                messages.error(request, "Error creating folder.")
        else:
            messages.error(request, "Folder name cannot be empty.")

    redirect_url = f"/?folder_id={parent_folder_id}" if parent_folder_id != 0 else "/"
    return redirect(redirect_url)

@login_required(login_url='login')
def share_file(request):
    if request.method == 'POST':
        file_id = request.POST.get('file_id')
        user_id = request.POST.get('user_id')
        permission = request.POST.get('permission')
        
        if file_id and user_id and permission:
            try:
                execute_query(
                    """
                    MATCH (f:File {id: $file_id}), (u:User {username: $user_id})
                    CREATE (f)-[r:SHARED_WITH {
                        permission: $permission,
                        since: $since
                    }]->(u)
                    RETURN f, r
                    """,
                    file_id=int(file_id),
                    user_id=user_id,
                    permission=permission,
                    since=datetime.now().isoformat()
                )
                messages.success(request, "File shared successfully!")
            except Exception as e:
                print(f"CognoDB node & relationship creation notice: {e}")
                messages.error(request, "Error sharing file.")
        else:
            messages.error(request, "Invalid file ID.")
    return redirect('/')

@login_required(login_url='login')
def get_shared_users(request):
    file_id = request.GET.get('file_id')
    if not file_id:
        return JsonResponse({'error': 'Missing file_id'}, status=400)
    
    # Ensure current user is the owner
    query = """
    MATCH (f:File {id: $file_id})-[:OWNED_BY]->(owner:User {username: $owner})
    OPTIONAL MATCH (f)-[r:SHARED_WITH]->(u:User)
    RETURN u.username AS username, r.permission AS permission, r.since AS since
    """
    
    try:
        result = execute_query(query, file_id=int(file_id), owner=request.user.username)
        users = []
        if result and hasattr(result, 'records'):
            for record in result.records:
                if record.get('username'):
                    users.append({
                        'username': record.get('username'),
                        'permission': record.get('permission'),
                        'since': record.get('since')
                    })
        return JsonResponse({'users': users})
    except Exception as e:
        print(f"Error fetching shared users: {e}")
        return JsonResponse({'error': 'Database error'}, status=500)

@login_required(login_url='login')
def remove_shared_user(request):
    if request.method == 'POST':
        file_id = request.POST.get('file_id')
        username = request.POST.get('username')
        if not file_id or not username:
            return JsonResponse({'error': 'Missing parameters'}, status=400)
            
        query = """
        MATCH (f:File {id: $file_id})-[:OWNED_BY]->(owner:User {username: $owner})
        MATCH (f)-[r:SHARED_WITH]->(u:User {username: $username})
        DELETE r
        """
        try:
            execute_query(query, file_id=int(file_id), owner=request.user.username, username=username)
            return JsonResponse({'success': True})
        except Exception as e:
            print(f"Error removing shared user: {e}")
            return JsonResponse({'error': 'Database error'}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required(login_url='login')
def check_user_exists(request):
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'exists': False})
    
    if username == request.user.username:
        # Don't let users share with themselves
        return JsonResponse({'exists': False, 'message': 'Cannot share with yourself'})
    
    query = "MATCH (u:User {username: $username}) RETURN count(u) AS count"
    try:
        result = execute_query(query, username=username)
        count = 0
        if result and hasattr(result, 'records'):
            count = result.records[0].get('count')
        return JsonResponse({'exists': count > 0})
    except Exception as e:
        print(f"Error checking user: {e}")
        return JsonResponse({'error': 'Database error'}, status=500)