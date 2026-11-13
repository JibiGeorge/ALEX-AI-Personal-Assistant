/**
 * Dynamic HUD Workspace Component (re-exporting HUDWorkspaceWindow)
 */

import { HUDWorkspaceWindow, type HUDWorkspaceWindowProps } from "./HUDWorkspaceWindow";
import type { WorkspaceActivity } from "../../types/workspace";

export interface HUDWorkspaceProps extends Omit<HUDWorkspaceWindowProps, "activity"> {
  activity: WorkspaceActivity;
}

export function HUDWorkspace(props: HUDWorkspaceProps) {
  return <HUDWorkspaceWindow {...props} />;
}

export { HUDWorkspaceWindow };
