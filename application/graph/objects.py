from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    """Node of a user"""
    id:int
    username: str
    email: Optional[str] = None
    

@dataclass
class File:
    """Node of a file"""
    id:int
    name:str
    url:str
    size: Optional[int] = None
    createdAt: Optional[str] = None
    deletedAt: Optional[str] = None
    parent_id:Optional[int] = None


@dataclass
class Folder:
    """Node of a folder"""
    id:int
    name:str
    createdAt: Optional[str] = None
    deletedAt: Optional[str] = None
    parent_id:Optional[int] = None
    

@dataclass
class OwnedBy:
    """Relationship from File/Folder to User : (User)-[:OWNED_BY]->(File/Folder)"""
    username:str
    fileorfolder_id:int
    type:str
    since: Optional[str] = None

    def parameters(self) -> dict[str, object]:
        return {
            "username": self.username,
            "fileorfolder_id": self.fileorfolder_id,
            "since": self.since,
        }


@dataclass
class ParentOf:
    """Relationship from File/Folder to Folder: (File/Folder)-[:PARENT_OF]->(Folder)"""
    parent_id:int
    child_id:int
    child_type:str
    since: Optional[str] = None


    def parameters(self) -> dict[str, object]:
        return {
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "since": self.since,
        }


@dataclass
class SharedWith:
    """Relationship from File to User: (File/Folder)-[:SHARED_WITH]->(User)"""
    file_id:int
    user_id:int
    permission:str
    since: Optional[str] = None


    def parameters(self) -> dict[str, object]:
        return {
            "file_id": self.file_id,
            "user_id": self.user_id,
            "since": self.since,
        }
