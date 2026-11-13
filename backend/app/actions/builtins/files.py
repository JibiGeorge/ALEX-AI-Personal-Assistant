from pydantic import BaseModel, ConfigDict, Field

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, ToolOutcome, done, unverified
from app.services.file_workspace_service import FileWorkspaceService


class StrictParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DirectoryParameters(StrictParameters):
    path: str = Field(default=".", min_length=1, max_length=1024)


class ReadParameters(StrictParameters):
    path: str = Field(min_length=1, max_length=1024)


class FindParameters(DirectoryParameters):
    query: str = Field(default="", max_length=200)
    extension: str = Field(default="", max_length=20)
    limit: int = Field(default=50, ge=1, le=50)


class WriteParameters(StrictParameters):
    path: str = Field(min_length=1, max_length=1024)
    content: str = Field(max_length=1_000_000)


class MoveParameters(StrictParameters):
    source: str = Field(min_length=1, max_length=1024)
    destination: str = Field(min_length=1, max_length=1024)


class RenameParameters(StrictParameters):
    path: str = Field(min_length=1, max_length=1024)
    new_name: str = Field(min_length=1, max_length=255)


class UndoParameters(StrictParameters):
    entry_id: str | None = Field(default=None, min_length=1, max_length=64)


def register_file_actions(
    registry: ActionRegistry,
    workspace: FileWorkspaceService,
) -> None:
    def handle_write(params: WriteParameters) -> ActionOutcomeResponse:
        res = workspace.write_text(params.path, params.content)
        try:
            target = workspace._resolve(params.path, allow_root=False)
            if not target.is_file() or target.stat().st_size != len(params.content.encode("utf-8")):
                return unverified("files.write", "File write initiated but destination state could not be verified.", data=res)
        except Exception:
            return unverified("files.write", "File write initiated but verification threw an exception.", data=res)
        return done("files.write", "File written and verified successfully.", data=res)

    registry.register(ActionDefinition(
        action_id="files.list",
        name="List workspace files",
        description="List files and folders inside Alex's private workspace only.",
        category="files",
        parameters=DirectoryParameters,
        handler=lambda params: done("files.list", "Directory listed.", data={"entries": workspace.list_directory(params.path), "items": workspace.list_directory(params.path)}),
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="files.read",
        name="Read workspace text file",
        description="Read a UTF-8 text file from Alex's private workspace (maximum 1 MiB).",
        category="files",
        parameters=ReadParameters,
        handler=lambda params: done("files.read", "File read successfully.", data=workspace.read_text(params.path)),
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="files.find",
        name="Find workspace files",
        description="Search file names inside Alex's private workspace; at most 50 results.",
        category="files",
        parameters=FindParameters,
        handler=lambda params: done(
            "files.find",
            "Files search completed.",
            data={
                "results": workspace.find_files(params.query, params.extension, params.path, params.limit),
                "matches": workspace.find_files(params.query, params.extension, params.path, params.limit),
            },
        ),
        timeout_seconds=10,
    ))
    registry.register(ActionDefinition(
        action_id="files.create_directory",
        name="Create workspace directory",
        description="Create a directory inside Alex's private workspace.",
        category="files",
        parameters=DirectoryParameters,
        handler=lambda params: done("files.create_directory", "Directory created.", data=workspace.create_directory(params.path)),
        timeout_seconds=5,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="files.write",
        name="Write workspace text file",
        description="Create or replace a UTF-8 text file inside Alex's private workspace.",
        category="files",
        parameters=WriteParameters,
        handler=handle_write,
        timeout_seconds=10,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="files.move",
        name="Move workspace file",
        description="Move a regular file within Alex's private workspace without overwriting.",
        category="files",
        parameters=MoveParameters,
        handler=lambda params: done("files.move", "File moved.", data=workspace.move_file(params.source, params.destination)),
        timeout_seconds=10,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="files.copy",
        name="Copy workspace file",
        description="Copy a regular file within Alex's private workspace without overwriting.",
        category="files",
        parameters=MoveParameters,
        handler=lambda params: done("files.copy", "File copied.", data=workspace.copy_file(params.source, params.destination)),
        timeout_seconds=10,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="files.rename",
        name="Rename workspace file",
        description="Rename a regular file inside Alex's private workspace without overwriting.",
        category="files",
        parameters=RenameParameters,
        handler=lambda params: done("files.rename", "File renamed.", data=workspace.rename_file(params.path, params.new_name)),
        timeout_seconds=10,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="files.trash",
        name="Move workspace file to Alex Trash",
        description="Move a regular workspace file into Alex's private, reversible Trash.",
        category="files",
        parameters=ReadParameters,
        handler=lambda params: done("files.trash", "File moved to trash.", data=workspace.trash_file(params.path)),
        timeout_seconds=10,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="files.undo_history",
        name="List reversible workspace changes",
        description="List recent reversible changes made inside Alex's private workspace.",
        category="files",
        parameters=StrictParameters,
        handler=lambda _: done("files.undo_history", "Undo history retrieved.", data={"history": workspace.undo_history()}),
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="files.undo",
        name="Undo workspace change",
        description="Undo the latest reversible workspace change, or a selected recent entry.",
        category="files",
        parameters=UndoParameters,
        handler=lambda params: done("files.undo", "Change undone.", data=workspace.undo(params.entry_id)),
        timeout_seconds=10,
        requires_confirmation=True,
    ))
