
# Ilusion Vault with CognoDB

Ilusion Vault is just a online storage for Files. It can be arranged in hierarchy with files and folders. The task was to use graph database for the storage of the data. 


## Features

- Save local files
- Store in hierarchical order with folder
- Share the files with other users easily
- Access the files easily through search and type of files


## Why Graph Database


For our use-case, using a Graph database is better idea because we are arranging the files and folders in hierarchical order. 

We can directly map the parent folder with its child file or folder. 

**Suppose, we want to query a file owned by a authorised user and it is a child of specific folder shared to someone.**

It will be little difficult to implement this structure in SQL databases. We have to join multiple tables to fetch such records causing the redundacy and performance issues as well.

Instead, if we use Graph databases, we just have to create a node for files/folders and just show the relationships with other nodes. In our case: 
- a file created by user 
- a file child of folder
- a file shared with user

It is much simpler to enhance the minor permissions as well with graph databases. We can even share the entire folder with the sensitivity lables added to the files inside.

##  Model (CognoDB )
A Graph Database architecture to natively represent file hierarchies, ownership, and complex permission structures can be added as well. 
Instead of traditional SQL joins, the architecture relies on **Nodes** and directional **Relationships** (Edges) for high-performance traversal.

<img width="776" height="736" alt="Screenshot from 2026-08-11 08-52-59" src="https://github.com/user-attachments/assets/48a31c8f-c2a6-4985-b376-09413196768b" />


### Nodes
Nodes represent the entities/objects within the vault ecosystem.
| Node Label | Properties | Description |
| :--- | :--- | :--- |
| `User` | -`id` (int) - `username` (str) - `email` (str) | Represents an authenticated platform user. |
| `Folder` | `id` (int)  - `name` (str)  - `createdAt` (datetime)  - `parent_id` (int) | Acts as a logical grouping mechanism for files and other sub-folders. |
| `File` | `id` (int)  - `name` (str)  - `url` (str)  - `size` (int)  - `createdAt` (datetime)  - `parent_id` (int) | Represents an encrypted object stored in Cloudflare R2. |
### Relationships (Edges)
Relationships define how nodes interact, governing hierarchy and access control.
| Relationship | Direction | Properties | Description |
| :--- | :--- | :--- | :--- |
| `OWNED_BY` | `(File/Folder) → (User)` | `type` (str)  - `since` (datetime) | Establishes the absolute owner of an asset. Evaluated first during permission checks. |
| `PARENT_OF` | `(Folder) → (File/Folder)` | `since` (datetime) | Defines the vault directory structure. Allows recursive graph traversal to fetch deeply nested assets. |
| `SHARED_WITH` | `(File) → (User)` | `permission` (str) | Grants access rights (e.g., `'read'`, `'delete'`) to non-owners without duplicating the underlying file node. |
### Querying the Hierarchy
Because directory structures are represented as Graph Relationships, retrieving a user's root directory is an efficient, single-hop traversal checking for items lacking a parent relationship, backed by a strict `parent_id` verification logic:
`WHERE f.parent_id IS NULL OR f.parent_id = 0`

## Queries Explained
Following are some of the queries used to query the data from graph database


**Fetch root files folders**

```
        //for Files
        MATCH (f:File)-[:OWNED_BY]->(u:User {username: $username})
        WHERE f.parent_id IS NULL OR f.parent_id = 0 OR f.parent_id = '0'
        RETURN f

        //for folders
        MATCH (f:Folder)-[:OWNED_BY]->(u:User {username: $username})
        WHERE f.parent_id IS NULL OR f.parent_id = 0 OR f.parent_id = '0'
        RETURN f

```
Fetch files and folders owned by the user and parent_id is NULL

**Fetch Shared files for current user**

```
        MATCH (f:File)-[r:SHARED_WITH]->(u:User {username: $username})
        RETURN f, r.permission AS permission
```
Fetch files which are shared with the current user and return the permission they are authorized for

**Create a new File node**

```
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

```

**Delete the file**
```
                MATCH (f:File {id: $id})
                WHERE (f)-[:OWNED_BY]->(:User {username: $username}) OR (f)-[:SHARED_WITH {permission: 'delete'}]->(:User {username: $username})
                DETACH DELETE f
                RETURN count(f) AS deleted_count

```

**Share file**
```
                    MATCH (f:File {id: $file_id}), (u:User {username: $user_id})
                    CREATE (f)-[r:SHARED_WITH {
                        permission: $permission,
                        since: $since
                    }]->(u)
                    RETURN f, r
```
## Setup and Instructions

Clone the project

```bash
  git clone https://github.com/shreyashrpawar/Ilusion-Graph
```

Go to the project directory

```bash
  cd Ilusion-Graph
```

Install dependencies

```bash
  pip install -r requirements.txt
```

Start the server

```bash
  python manage.py runserver
```

Add following fields in .env

```bash
COGNODB_URI=bolt+s://xyx
COGNODB_USER=___
COGNODB_PASSWORD=___
R2_ACCOUNT_ID=___
R2_ACCESS_KEY_ID=___
R2_SECRET_ACCESS_KEY=___
R2_BUCKET_NAME=__
R2_ENDPOINT=___
R2_USE_PATH_STYLE_ENDPOINT=___

```

TO generate the COGNODB credentials
```
Create an instance
Sign up and create a free c0 instance. It provisions in well under a minute and you pick the region
```

## Screenshot of the UI

<img width="1915" height="955" alt="Screenshot from 2026-08-11 09-19-53" src="https://github.com/user-attachments/assets/fab0db99-2f25-423d-b67b-012f8a9b00ca" />


## Hosted application Link and Recording

URL: https://ilusion.one

[Screencast from 2026-08-11 09-23-57.webm](https://github.com/user-attachments/assets/f9b388b3-a9e4-4f58-82c2-a9c28f2b205f)





