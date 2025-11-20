# utils/save_excel.py
import os
import io
import pandas as pd
from tkinter import messagebox, filedialog
import matplotlib.pyplot as plt
from openpyxl.drawing.image import Image as OpenpyxlImage

def save_to_excel(df, settings, vehicle_counts):
    if df.empty:
        messagebox.showinfo("Info", "No data to save.")
        return

    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)

    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")],
        title="Save Detection Data"
    )

    if not file_path:
        return

    try:
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Summary
            df.to_excel(writer, sheet_name='Summary', index=False)

            start_time = pd.to_datetime(settings.get("start_timestamp_user") or df['Timestamp'].iloc[0])
            df_copy = df.copy()
            df_copy['Timestamp'] = pd.to_datetime(df_copy['Timestamp'])

            # Hourly
            df_copy['hour'] = ((df_copy['Timestamp'] - start_time).dt.total_seconds() // 3600).astype(int)
            df_copy['hour_str'] = df_copy['hour'].apply(lambda x: (start_time + pd.Timedelta(hours=x)).strftime("%Y-%B-%d %H:00:00"))
            hourly = df_copy.groupby(['hour_str', 'Class']).size().reset_index(name='Overall')
            hourly_pivot = hourly.pivot_table(index='hour_str', columns='Class', values='Overall', fill_value=0).reset_index()
            hourly_pivot.rename(columns={'hour_str': 'Time'}, inplace=True)
            hourly_pivot.to_excel(writer, sheet_name='Hourly Data', index=False)

            # Daily
            df_copy['day_str'] = df_copy['Timestamp'].dt.strftime("%Y-%m-%d \n %A")
            daily = df_copy.groupby(['day_str', 'Class']).size().reset_index(name='Overall')
            daily_pivot = daily.pivot_table(index='day_str', columns='Class', values='Overall', fill_value=0).reset_index()
            daily_pivot.rename(columns={'day_str': 'Date'}, inplace=True)
            daily_pivot.to_excel(writer, sheet_name='Daily Data', index=False)

            # Monthly
            df_copy['mon_str'] = df_copy['Timestamp'].dt.strftime("%B-%Y")
            monthly = df_copy.groupby(['mon_str', 'Class']).size().reset_index(name='Overall')
            monthly_pivot = monthly.pivot_table(index='mon_str', columns='Class', values='Overall', fill_value=0).reset_index()
            monthly_pivot.rename(columns={'mon_str': 'Date'}, inplace=True)
            monthly_pivot.to_excel(writer, sheet_name='Monthly Data', index=False)

            fig, ax = plt.subplots(figsize=(10,6))
            summary_data = []
            for golongan, counts in vehicle_counts.items():
                                    summary_data.append([golongan, counts["In"], counts["Out"]])
            summary_df = pd.DataFrame(summary_data, columns=["Golongan", "Total In", "Total Out"])
            summary_df.set_index("Golongan")[["Total In", "Total Out"]].plot(kind='bar', ax=ax)

            ax.set_title('Vehicle In/Out Counts by Golongan')
            ax.set_ylabel('Count')
            ax.set_xlabel('Class')
            plt.xticks(rotation=45, ha='right')        
            plt.tight_layout()
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', bbox_inches='tight')
            img_buf.seek(0)
            plt.close(fig)

            img_sheet_name = 'Summary Chart'
            img_sheet = writer.book.create_sheet(img_sheet_name)
            img_sheet.title = img_sheet_name

            img_openpyxl = OpenpyxlImage(img_buf)
            img_openpyxl.anchor = 'A1'
            img_sheet.add_image(img_openpyxl)
            
            

        messagebox.showinfo("Success", f"Data saved to {file_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to save data: {e}")
