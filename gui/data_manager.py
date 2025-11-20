import pandas as pd


class DataManager:
    def __init__(self, app):
        self.app = app
        self.df = pd.DataFrame(columns=["Timestamp", "Vehicle ID", "Class", "Direction"])
        self.golongan_list = ["Gol 1", "Gol 2", "Gol 3", "Gol 4", "Gol 5", "Motor"]
        self.vehicle_counts = {golongan: {"In": 0, "Out": 0} for golongan in self.golongan_list}

    def reset_data(self, clear_all=False):
        """Reset data - either all data or just counts"""
        if clear_all:
            # If clear_all=True, clear all data
            self.df = self.df.iloc[0:0]
            self.vehicle_counts = {golongan: {"In": 0, "Out": 0} for golongan in self.golongan_list}
        else:
            # If clear_all=False (default), only reset count for new video
            self.vehicle_counts = {golongan: {"In": 0, "Out": 0} for golongan in self.golongan_list}

        self.update_gui_display()

    def update_gui_display(self):
        """Update GUI display with current data"""
        # Clear existing items
        for i in self.app.ui_components.tree.get_children(): 
            self.app.ui_components.tree.delete(i)
        
        # Add new items
        for _, row in self.df.iterrows():
            self.app.ui_components.tree.insert("", "end", values=list(row))
        
        # Scroll to bottom if there's data
        if not self.df.empty: 
            self.app.ui_components.tree.yview_moveto(1)

    def add_detection_data(self, new_rows):
        """Add new detection data"""
        new_df = pd.DataFrame(new_rows)
        self.df = pd.concat([self.df, new_df], ignore_index=True)
        self.update_gui_display()

    def get_export_data(self):
        """Get data for export"""
        return {
            'df': self.df,
            'vehicle_counts': self.vehicle_counts,
            'settings': self.app.settings
        }