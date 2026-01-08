import re
import pymupdf
from enum import Enum
from pathlib import Path
from dataclasses import dataclass

DOC_TYPE_KEYWORDS = {'Договор за засновање претплатнички однос за користење': [],
                     'Договор за купопродажба на уреди со одложено плаќање на рати': [],
                     'Договор за користење на јавни комуникациски услуги': ['за користење на Јавни комуникациски услуги бр.', 'на ден', 'помеѓу', 
                                                                            '2. ПРЕТПЛАТНИК', 'физичко лице', 'правно лице', 'ЕМБГ'],
                     'Договор за користење на јавни комуникациски услуги': [],
                     'БАРАЊЕ ЗА ПРЕНЕСУВАЊЕ НА УСЛУГИ ПОМЕЃУ РАЗЛИЧНИ БАН БРОЕВИ КОИ ПРИПАЃААТ НА ИСТ ПРЕТПЛАТНИК': []}


regs = {'3': [
    r'бр\.\s*(\d+)',
    r'на ден\s+(\b[0-9\.]*\b)\s+помеѓу',
    r'(?<=ПРЕТПЛАТНИК)(.*)(?=правно лице)',
    r'ЕМБГ:\s+(\b[0-9]+\b)'
    ]}

class KeywordPosition(Enum):
    BEFORE=1
    IN_BETWEEN=2
    AFTER=3

@dataclass
class MatchingConditions:
    length : int
    is_following : bool
    is_preceding : bool
    has_digits : bool
    match_front : bool
    match_back : bool

@dataclass
class KeywordBounds:
    preceding: str
    following: str


def create_regex_expression(preceding : str, following : str) -> str:
    reg = ""
    #keyword in middle
    if preceding and following:
        reg = f"(?<={preceding})(.*)(?={following})"
    elif preceding and not following:
        if '.' in preceding:
            preceding= preceding.replace('.', '\\.')
        reg = f"{preceding}\\s+(\\d+)"
    return reg

@dataclass
class MatchingStruct:
    keyword : str
    preceding : str
    following : str
    re_expression : str

class OcrHandler:
    def __init__(self, title : str):
        self.title = title
        self.bounds = self.generate_matching_structs()
    def generate_matching_structs(self) -> list[MatchingStruct]:
        match self.title:
            case 'Договор за засновање претплатнички однос за користење':
                return [
                    MatchingStruct(
                        keyword='BAN',
                        preceding='за користење на Јавни комуникациски услуги бр.',
                        following='',
                        re_expression=create_regex_expression(preceding='за користење на Јавни комуникациски услуги бр.', following='')
                    ),
                    MatchingStruct(
                        keyword='date',
                        preceding='на ден', 
                        following='помеѓу',
                        re_expression=create_regex_expression(preceding='на ден', following='помеѓу')
                    ),
                    MatchingStruct(
                        keyword='customer_type_resident',
                        preceding='ПРЕТПЛАТНИК', 
                        following='правно лице',
                        re_expression=create_regex_expression(preceding='ПРЕТПЛАТНИК', following='правно лице')
                    ),
                    MatchingStruct(
                        keyword='customer_type_businnes',
                        preceding='ПРЕТПЛАТНИК', 
                        following='правно лице',
                        re_expression=create_regex_expression(preceding='ПРЕТПЛАТНИК', following='правно лице')
                    ),
                    MatchingStruct(
                        keyword='EMBG_EDB',
                        preceding='ПРЕТПЛАТНИК', 
                        following='правно лице',
                        re_expression=create_regex_expression(preceding='ЕМБГ:', following='')
                    )
                    ]
            case 'Договор за купопродажба на уреди со одложено плаќање на рати':
                return [
                    # KeywordBounds(keyword='a', preceding='b', following='c')
                    ]
            case 'Договор за користење на јавни комуникациски услуги':
                return [
                    # KeywordBounds(keyword='a', preceding='b', following='c')
                    ]
            case 'Договор за користење на јавни комуникациски услуги':
                return [
                    # KeywordBounds(keyword='a', preceding='b', following='c')
                    ]
            case 'БАРАЊЕ ЗА ПРЕНЕСУВАЊЕ НА УСЛУГИ ПОМЕЃУ РАЗЛИЧНИ БАН БРОЕВИ КОИ ПРИПАЃААТ НА ИСТ ПРЕТПЛАТНИК':
                return [
                    # KeywordBounds(keyword='a', preceding='b', following='c')
                    ]
            case _:
                return []

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

def extract_content_from_page(page : pymupdf.Page) -> str:
    block = page.get_text("blocks", sort=True)
    block = str(page.get_text("text", sort=True))
    block = re.sub('\n', '  ', block) #It is necessary to map it to more than just 1 space (2 or higher)
    # block = re.sub(r' {2,}', '\n', block)
    block = re.sub(r' {2,}', ' ', block)
    # block = re.sub(' +', '', block)
    # block = block.split("\n")
    return block

def modify_customer_type_info(d : dict[str, str]) -> None:
    matched_string = d.get('customer_type_resident', 'CHECK KEY!!')
    print(f"{matched_string=}")
    x_char_index = -1
    try:
        x_char_index = matched_string.index(chr(0x445)) #This is Macedonian/Cyrilic 'x'
    except ValueError:
        x_char_index = matched_string.index(chr(0x78)) #This is Lating 'x'
    if x_char_index == -1:
        raise RuntimeError("Customer type might not have been selected or character case mixed (lower - should be upper or reverse)")
    elif x_char_index <= 0.2 * len(matched_string):
        d['customer_type_resident'] = "X"
        d['customer_type_businnes']  = ""
    else:
        d['customer_type_resident'] = ""
        d['customer_type_businnes']  = "X"
    return

def match_expressions(matching_structs : list[MatchingStruct], file_content : str) -> dict[str, str | bool]:
    result = {}
    for struct in matching_structs:
        print(f"MATCHING expression: {struct.re_expression}")
        match = re.search(struct.re_expression.lower(), file_content.lower(), re.DOTALL)
        if match:
            result[struct.keyword] = match.group(1).strip()
    modify_customer_type_info(result)
    return result
def main():
    root_folder_path_obj = Path(__file__).parent
    # print(list(root_folder_path_obj.iterdir()))
    file_name = ""
    for x in root_folder_path_obj.iterdir():
        if x.is_file() and x.name.endswith("pdf"):
            print(f"File name: {x.stem}, file name + type: {x.name}")
            file_name = x.name
    # print(f"{file_path_obj=}")
    doc = pymupdf.open(Path(root_folder_path_obj / file_name))
    print(f"file name: {root_folder_path_obj}")
    doc_path = None
    if not is_regular_pdf_page(doc[0]):
        doc_path = convert_img_to_pdf(doc[0])
    if doc_path:
        doc = pymupdf.open(doc_path)
    pdf_content = extract_content_from_page(doc[0])
    ocrHandler = OcrHandler(file_name.split(".")[0])
    for bound in ocrHandler.bounds:
        print(bound.re_expression)
    # print(f"{pdf_content=}")
    print(f"{match_expressions(ocrHandler.bounds, pdf_content)=}")
    return

if __name__ == "__main__":
    main()