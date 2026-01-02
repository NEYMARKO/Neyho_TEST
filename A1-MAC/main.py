import re
import pymupdf
from pathlib import Path

DOC_TYPE_KEYWORDS = {'Договор за засновање претплатнички однос за користење': [],
                     ' Договор за купопродажба на уреди со одложено плаќање на рати': [],
                     'Договор за користење на јавни комуникациски услуги': ['за користење на Јавни комуникациски услуги бр.', 'на ден', 'помеѓу', 
                                                                            '2. ПРЕТПЛАТНИК', 'физичко лице', 'правно лице', 'ЕМБГ'],
                     'Договор за користење на јавни комуникациски услуги': [],
                     'БАРАЊЕ ЗА ПРЕНЕСУВАЊЕ НА УСЛУГИ ПОМЕЃУ РАЗЛИЧНИ БАН БРОЕВИ КОИ ПРИПАЃААТ НА ИСТ ПРЕТПЛАТНИК': []}

# def get_keywords_for_doc_type(doc_type)

def is_regular_pdf_page(page : pymupdf.Page) -> bool:
    text_blocks = 0
    image_blocks = 0
    content = page.get_text("dict")
    for b in content.get('blocks', []):
        if (b['type'] == 0):
            text_blocks += 1
        elif (b['type'] == 1):
            image_blocks += 1
    print(f"{text_blocks=}")
    print(f"{image_blocks=}")
    return text_blocks > 0

def convert_img_to_pdf(page : pymupdf.Page) -> Path:
    root_folder_path_obj = Path(__file__).parent
    image_output_folder_path_obj = root_folder_path_obj / "imgs"
    image_list = page.get_images()
    if not image_list:
        raise RuntimeError("Unable to locate images on a page")
    res = 72
    matrix = pymupdf.Matrix(300/res, 300/res)
    pix = page.get_pixmap(matrix=matrix)
    if pix.alpha:
        pix.set_alpha(None)
    gamma = 1.35
    pix.gamma_with(gamma)
    img_path = f"{image_output_folder_path_obj.absolute()}/res_{res}-gamma_{gamma}.png"
    pix.save(str(img_path))
    
    doc_name = str(img_path)[:-3] + "pdf"
    pix.pdfocr_save(doc_name, language="mkd")
    return Path(doc_name)

def extract_content_from_page(page : pymupdf.Page) -> list[str]:
    block = page.get_text("blocks", sort=True)
    block = page.get_text("text", sort=True)
    block = re.sub('\n', '  ', block) #It is necessary to map it to more than just 1 space (2 or higher)
    block = re.sub(r' {2,}', '\n', block)
    # block = re.sub(' +', '', block)
    block = block.split("\n")
    return block

def main():
    root_folder_path_obj = Path(__file__).parent
    print(root_folder_path_obj) 
    doc = pymupdf.open(Path(root_folder_path_obj / "b.pdf"))

    doc_path = None
    if not is_regular_pdf_page(doc[0]):
        doc_path = convert_img_to_pdf(doc[0])
    if doc_path:
        doc = pymupdf.open(doc_path)
    pdf_content = extract_content_from_page(doc[0])
    print(f"{pdf_content=}")
    return

if __name__ == "__main__":
    main()