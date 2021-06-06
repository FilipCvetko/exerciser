import PySimpleGUI as sg
from config import *

window = sg.Window(title="Exerciser", layout=layout, resizable=True)

while True:
    event, values = window.read()

    if event == "OK" or event == sg.WIN_CLOSED:
        break

    if event == "-FOLDER-":
        dir = values["-FOLDER-"]
        full_fnames = [fname for fname in os.listdir(dir) if fname.endswith(".pdf")]
        window["-TEXTBOOK_LIST-"].update(full_fnames)

    if event == "-SEARCH-":
        text = values["-INPUT-"]
        textbook_file = values["-TEXTBOOK_LIST-"]
        to_open = (os.path.join(values["-FOLDER-"], textbook_file[0]))
        gen_obj = search(text, file=to_open)
        try:
            filename = next(gen_obj)
            window["-IMAGE-"].update(filename=filename)
           # window["-IMAGE-"].set_size(img_size)
        except:
            pass

    if event == "-NO-":
        try:
            filename = next(gen_obj)
            print(filename)
            window["-IMAGE-"].update(filename=filename)
            #window["-IMAGE-"].set_size(img_size)
        except:
            pass