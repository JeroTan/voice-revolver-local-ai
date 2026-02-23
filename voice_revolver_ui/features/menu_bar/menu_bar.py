"""
Menu Bar - Application menu bar with workspace switching

Provides:
- Workspace menu (switch between features)
- View menu (show/hide logs)
"""

import tkinter as tk


class MenuBar:
    """Application menu bar"""
    
    def __init__(self, root, on_toggle_logs=None, log_callback=None):
        """Initialize menu bar.
        
        Args:
            root: Root window
            on_toggle_logs: Callback for toggle logs command
            log_callback: Optional callback for logging messages
        """
        self.root = root
        self.on_toggle_logs = on_toggle_logs
        self.log_callback = log_callback
        self.workspace_items = {}  # Store workspace menu items by ID
        self.active_workspace = "vocal_changer"  # Track active workspace
        
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
        
        # Workspaces - created without commands initially
        # Commands will be set via enable_workspace()
        workspace_menu.add_command(label="Vocal Changer")
        self.workspace_items["vocal_changer"] = 0
        
        workspace_menu.add_command(label="Audio Separation")
        self.workspace_items["audio_separation"] = 1
        
        workspace_menu.add_command(label="Text to Speech")
        self.workspace_items["text_to_speech"] = 2
        
        workspace_menu.add_command(label="Voice Cloning (Coming Soon)")
        self.workspace_items["voice_cloning"] = 3
        
        workspace_menu.add_command(label="Voice Training (Coming Soon)", state="disabled")
        self.workspace_items["voice_training"] = 4
        
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
    
    def set_active_workspace(self, workspace_id: str):
        """Set the active workspace in the menu.
        
        Args:
            workspace_id: ID of the workspace (e.g., "vocal_changer")
        """
        self.active_workspace = workspace_id
        
        # Update all workspace menu items to show/hide checkmark
        for ws_id, menu_index in self.workspace_items.items():
            try:
                current_label = self.workspace_menu.entrycget(menu_index, "label")
                current_state = self.workspace_menu.entrycget(menu_index, "state")
                
                # Skip if item is disabled (Coming Soon items)
                if current_state == "disabled":
                    continue
                
                # Remove checkmark if present
                clean_label = current_label.replace("✓ ", "")
                
                # Add checkmark to active workspace
                if ws_id == workspace_id:
                    new_label = f"✓ {clean_label}"
                else:
                    new_label = clean_label
                
                self.workspace_menu.entryconfig(menu_index, label=new_label)
            except tk.TclError:
                pass  # Skip separator or invalid items
    
    def enable_workspace(self, workspace_id: str, command):
        """Enable a workspace menu item.
        
        Args:
            workspace_id: ID of the workspace (e.g., "audio_separation")
            command: Callback when workspace is selected
        """
        if workspace_id in self.workspace_items:
            menu_index = self.workspace_items[workspace_id]
            try:
                current_label = self.workspace_menu.entrycget(menu_index, "label")
                # Remove "Coming Soon" suffix and checkmark
                clean_label = current_label.replace(" (Coming Soon)", "").replace("✓ ", "")
                
                # Set the command for the menu item
                self.workspace_menu.entryconfig(
                    menu_index,
                    label=clean_label,
                    command=command
                )
            except tk.TclError as e:
                if self.log_callback:
                    self.log_callback(f"[MenuBar ERROR] Failed to enable '{workspace_id}': {e}")
