
from tkinter import *
import tkinter
import random
from datetime import datetime 
class Freq:
    def __init__(self):
        self.root = tkinter.Tk()
        #self.root.attributes("-topmost",True)
        #self.root.overrideredirect(True)
        self.root.geometry("197x96+941+538")
        self.root.configure(background='black')
        self.rng()
        self.label = tkinter.Label(self.root,text=self.rng_num,bg="black",fg="white",width=16,font=("Helvetica", 32))
        self.label.pack()
        #self.rng_button = tkinter.Button(self.root,text="RNG",bg="black",fg="white",command= self.rng,width=12,height=2)
        #self.rng_button.pack()
        self.root.bind("<Button-1>",lambda e:self.rng())
        self.root.mainloop()
    def rng(self):
        random.seed(str(datetime.now()))
        self.rng_num= str( random.randint(0,100))
        try:
            self.label.configure(text = self.rng_num)
        except:
            pass

Freq()