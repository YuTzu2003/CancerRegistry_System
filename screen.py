import customtkinter as ctk
from tkinter import filedialog
import pandas as pd
import os

class DeidApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("醫療資料清洗系統")
        self.geometry("1000x850")
        ctk.set_appearance_mode("dark")
        self.df = None
        
        current_path = os.path.dirname(os.path.realpath(__file__))
        ico_path = os.path.join("data_cleaning.ico")
        if os.path.exists(ico_path): self.iconbitmap(ico_path)
        self.setup_ui()

    def setup_ui(self):
        self.header = ctk.CTkLabel(self, text="醫療資料清洗系統", font=("Microsoft JhengHei", 24))
        self.header.pack(pady=20)

        self.op_frame = ctk.CTkFrame(self)
        self.op_frame.pack(pady=10, padx=20, fill="x")

        self.btn_load = ctk.CTkButton(self.op_frame, text="選擇檔案", command=self.load_file)
        self.btn_load.grid(row=0, column=0, padx=10, pady=10)

        self.file_label = ctk.CTkLabel(self.op_frame, text="尚未選擇檔案", text_color="gray")
        self.file_label.grid(row=0, column=1, padx=10)

        self.btn_nat = ctk.CTkButton(self.op_frame, text="輸出全國欄位資料", fg_color="#34495e")
        self.btn_nat.grid(row=0, column=2, padx=10)

        self.btn_yl = ctk.CTkButton(self.op_frame, text="輸出台大雲林欄位資料", fg_color="#2c3e50")
        self.btn_yl.grid(row=0, column=3, padx=10)

        self.stats_lbl = ctk.CTkLabel(self, text="正確率：--% | 總件數：0 | 錯誤件數：0", font=("Microsoft JhengHei", 15, "bold"))
        self.stats_lbl.pack(pady=5)
        
        self.log_box = ctk.CTkTextbox(self, height=450, font=("Consolas", 12))
        self.log_box.pack(pady=10, padx=20, fill="both", expand=True)
        self.log_box.tag_config("error", foreground="#ff4d4d")

        self.btn_run = ctk.CTkButton(self, text="執行資料清洗", fg_color="#27ae60", font=("Microsoft JhengHei", 16))
        self.btn_run.pack(pady=20)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV Files", "*.csv"), ("All Files", "*.*")])
        if path:
            self.file_label.configure(text=os.path.basename(path), text_color="white")
            self.df = pd.read_excel(path, dtype=str) if path.endswith(('.xlsx', '.xls')) else pd.read_csv(path, dtype=str)

if __name__ == "__main__":
    DeidApp().mainloop()