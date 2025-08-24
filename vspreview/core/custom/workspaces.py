from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget
from ...plugins.abstract import WorkspacePlugin

if TYPE_CHECKING:
    from ...main import MainWindow
    from ...plugins.abstract import WorkspacePlugin


class WorkspaceManager:
    """Manages workspace plugins and the workspace bar UI."""

    def __init__(self, main_window: MainWindow) -> None:
        self.main_window = main_window
        self.workspace_plugins = dict[str, WorkspacePlugin]()
        self.workspace_bar: QWidget = QFrame()
        self.workspace_buttons_layout: QHBoxLayout = QHBoxLayout()

    def create_workspace_bar(self) -> QWidget:
        """Create the workspace bar with workspace buttons."""
        workspace_bar = QFrame()
        workspace_bar.setObjectName("workspace_bar")

        layout = QHBoxLayout(workspace_bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        workspace_label = QLabel("WORKSPACES")

        buttons_frame = QFrame()
        buttons_frame.setObjectName("buttons_container")
        

        self.workspace_buttons_layout = QHBoxLayout(buttons_frame)
        self.workspace_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.workspace_buttons_layout.setSpacing(4)

        layout.addWidget(workspace_label)
        layout.addWidget(buttons_frame, 1)
        layout.addStretch(1)

        self._add_workspace_button("Default", None)

        self.workspace_bar = workspace_bar
        return workspace_bar

    def _add_workspace_button(self, name: str, workspace_plugin: WorkspacePlugin | None) -> None:
        """Add a workspace button to the workspace bar."""
        button = QPushButton(name)
        button.setCheckable(True)
        button.setMinimumHeight(28)

        if workspace_plugin is None:
            button.setChecked(True)
            button.clicked.connect(lambda: self._switch_to_workspace(None))
        else:
            button.clicked.connect(lambda: self._switch_to_workspace(workspace_plugin))

        self.workspace_buttons_layout.addWidget(button)
        button.setProperty("workspace_plugin", workspace_plugin)

    def _switch_to_workspace(self, workspace_plugin: WorkspacePlugin | None) -> None:
        """Switch to the specified workspace."""
        try:
            # update button here
            for i in range(self.workspace_buttons_layout.count()):
                widget = self.workspace_buttons_layout.itemAt(i).widget()
                if hasattr(widget, 'setChecked'):
                    plugin = widget.property("workspace_plugin")
                    widget.setChecked(plugin is workspace_plugin)

            print(f"Switching to workspace: {workspace_plugin.__class__.__name__ if workspace_plugin else 'None'}")
            self.main_window.graphics_view.set_active_workspace(workspace_plugin)

            # refresh the graphics view here
            self.main_window.graphics_view.setup_view()
            self.main_window.graphics_view.update()

            if workspace_plugin:
                workspace_name = workspace_plugin.get_workspace_display_name()
                self.main_window.show_message(f"🎯 Switched to workspace: {workspace_name}")
                print(f"[WORKSPACE] Activated: {workspace_name}")
            else:
                self.main_window.show_message("🎯 Switched to default workspace")
                print("[WORKSPACE] Activated: Default workspace")

        except Exception as e:
            print(f"[WORKSPACE ERROR] Failed to switch workspace: {e}")
            self.main_window.show_message(f"❌ Workspace switch failed: {str(e)}")

    def add_workspace_plugin(self, workspace_plugin: WorkspacePlugin) -> None:
        """Add a workspace plugin to the workspace bar."""
        workspace_name = workspace_plugin.get_workspace_display_name()

        plugin_namespace = getattr(workspace_plugin._config, 'namespace', str(id(workspace_plugin)))
        self.workspace_plugins[plugin_namespace] = workspace_plugin
        print(f"WorkspaceManager: Added workspace plugin {workspace_plugin.__class__.__name__} with namespace {plugin_namespace}")
        self._add_workspace_button(workspace_name, workspace_plugin)
