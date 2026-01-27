import re
import pymupdf
from pathlib import Path

def main():
    root_folder_path_obj = Path(__file__).parent
    print(root_folder_path_obj) 
    doc = pymupdf.open(Path(root_folder_path_obj / "b.pdf"))
    # print(f"{doc.metadata=}")
    i = 1
    page = doc[0]
    block = page.get_text("blocks", sort=True)
    block = page.get_text("text", sort=True)
    block = re.sub('\n', '  ', block) #It is necessary to map it to more than just 1 space (2 or higher)
    block = re.sub(r' {2,}', '\n', block)
    # block = re.sub(' +', '', block)
    block = block.split("\n")
    # print(f"{block=}\n\n")

    print(" ".join(block))
    # for element in block:
    #     print(element)
    # words = page.get_text("xml")
    # print(f"{words=}")
    # for page in doc:
    #     print(f"PAGE {i}")
    #     text = page.get_text("blocks")
    #     print(text)
    #     i += 1
    return

if __name__ == "__main__":
    main()