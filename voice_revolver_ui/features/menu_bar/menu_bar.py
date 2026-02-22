"""
Menu Bar - Application menu bar with workspace switching

Provides:
- Workspace menu (switch between features)
- View menu (show/hide logs)
"""

import tkinter as tk


class MenuBar:
    """Application menu bar"""
    
    def __init__(self, root, on_toggle_logs=None):
        """Initialize menu bar.
        
        Args:
            root: Root window
            on_toggle_logs: Callback for toggle logs command
        """
        self.root = root
        self.on_toggle_logs = on_toggle_logs
        
        self.menubar = tk.Menu(root)
        root.config(menu=self.menubar)
        
        self._build_menus()
        self._setup_keyboard_shortcuts()
    
    def _build_menus(self):
        """Build all menus"""
        self._build_workspace_menu()
        self._build_view_menu()
    
    def _build_workspace_menu(self):
        """Build workspace menu"""
        workspace_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Workspace", menu=workspace_menu)
        
        # Current workspace (disabled/checked)
        workspace_menu.add_command(label="✓ Vocal Changer", state="disabled")
        workspace_menu.add_separator()
        
        # Future workspaces (disabled until implemented)
        workspace_menu.add_command(label="Audio Separation (Coming Soon)", state="disabled")
        workspace_menu.add_command(label="Text to Speech (Coming Soon)", state="disabled")
        workspace_menu.add_command(label="Voice Cloning (Coming Soon)", state="disabled")
        workspace_menu.add_command(label="Voice Training (Coming Soon)", state="disabled")
        
        self.workspace_menu = workspace_menu
    
    def _build_view_menu(self):
        """Build view menu"""
        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=view_menu)
        
        # Toggle logs command
        if self.on_toggle_logs:
            view_menu.add_command(label="Show/Hide Logs (F12)", command=self.on_toggle_logs)
        
        self.view_menu = view_menu
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        if self.on_toggle_logs:
            self.root.bind('<F12>', lambda e: self.on_toggle_logs())
    
    def set_active_workspace(self, workspace_name: str):
        """Set the active workspace in the menu.
        
        Args:
            workspace_name: Name of the workspace (e.g., "Vocal Changer")
        """
        # Update menu to show new active workspace
        # This will be implemented when we have multiple workspaces
        pass
    
    def enable_workspace(self, workspace_name: str, command):
        """Enable a workspace menu item.
        
        Args:
            workspace_name: Name of the workspace
            command: Callback when workspace is selected
        """
        # This will be implemented when we have multiple workspaces
        pass
