

import tkinter as tk

class Example(tk.Frame):
    def __init__(self, root):
        tk.Frame.__init__(self, root)
        b1 = tk.Button(self, text="Add another window", command = self.newWindow)
        b1.pack(side="top", padx=40, pady=40)
        self.count = 0

    def newWindow(self):
        self.count += 1
        window = tk.Toplevel(self)
        label = tk.Label(window, text="This is window #%s" % self.count)
        label.pack(side="top", fill="both", expand=True, padx=40, pady=40);
        b1 = tk.Button(self, text="Add another window", command = self.newWindow)
        
if __name__ == "__main__":
    root = tk.Tk()
    Example(root).pack(side="top", fill="both", expand=True)
    root.mainloop()