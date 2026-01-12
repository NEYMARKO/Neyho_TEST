import re
import cv2
import fitz
import pymupdf
import numpy as np
from pathlib import Path
from dataclasses import dataclass
DOC_TYPE_KEYWORDS = {'Договор за засновање претплатнички однос за користење': [],
                     'Договор за купопродажба на уреди со одложено плаќање на рати': [],
                     'Договор за користење на јавни комуникациски услуги': ['за користење на Јавни комуникациски услуги бр.', 'на ден', 'помеѓу', 
                                                                            '2. ПРЕТПЛАТНИК', 'физичко лице', 'правно лице', 'ЕМБГ'],
                     'Договор за користење на јавни комуникациски услуги': [],
                     'БАРАЊЕ ЗА ПРЕНЕСУВАЊЕ НА УСЛУГИ ПОМЕЃУ РАЗЛИЧНИ БАН БРОЕВИ КОИ ПРИПАЃААТ НА ИСТ ПРЕТПЛАТНИК': []}

DATE_REGEXES = [
    "\\d{2}\\.\\d{2}.\\d{2,4}",
    "\\d{2}\\-\\d{2}-\\d{2,4}"
]

regs = {'3': [
    r'бр\.\s*(\d+)',
    r'на ден\s+(\b[0-9\.]*\b)\s+помеѓу',
    r'(?<=ПРЕТПЛАТНИК)(.*)(?=правно лице)',
    r'ЕМБГ:\s+(\b[0-9]+\b)'
    ]}

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
    bounds : tuple[float, float, float, float]

DOCUMENT_LAYOUT = {
    'Договор за засновање претплатнички однос за користење': 
    {
        'bounds': 
        [
            {
                'table': [
                    (0.075, 0.175),
                    (0.925, 0.275)
                ]
            },
            {
                'checkbox': [
                    (0.225, 0.175),
                    (0.6, 0.21)
                ]
            }
        ]
    }
}

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
                        re_expression=create_regex_expression(preceding='за користење на Јавни комуникациски услуги бр.', following=''),
                        bounds=(149.89999389648438, 89.13378143310547, 418.451416015625, 100.3326644897461)
                    ),
                    MatchingStruct(
                        keyword='date',
                        preceding='на ден', 
                        following='помеѓу',
                        re_expression=create_regex_expression(preceding='на ден', following='помеѓу'),
                        bounds=(150.13999938964844, 102.10941314697266, 333.99322509765625, 109.52684783935547)
                    ),
                    MatchingStruct(
                        keyword='customer_type_resident',
                        preceding='ПРЕТПЛАТНИК', 
                        following='правно лице',
                        re_expression=create_regex_expression(preceding='ПРЕТПЛАТНИК', following='правно лице'),
                        bounds=(76.58399963378906, 143.26937866210938, 220.76547241210938, 150.68682861328125)
                    ),
                    MatchingStruct(
                        keyword='customer_type_businnes',
                        preceding='ПРЕТПЛАТНИК', 
                        following='правно лице',
                        re_expression=create_regex_expression(preceding='ПРЕТПЛАТНИК', following='правно лице'),
                        bounds=(316.6099853515625, 143.26937866210938, 356.92291259765625, 150.68682861328125)
                    ),
                    MatchingStruct(
                        keyword='EMBG_EDB',
                        preceding='ПРЕТПЛАТНИК', 
                        following='правно лице',
                        re_expression=create_regex_expression(preceding='ЕМБГ:', following=''),
                        bounds=(76.58399963378906, 177.46939086914062, 104.63197326660156, 184.8868408203125)
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


def split_document_with_rectangular_contours(img_path : str, section_cnt : int, direction : int = 0) -> None:
    img = cv2.imread(img_path)
    width = img.shape[1]
    height = img.shape[0]
    horizontal_contour_rects = []
    vertical_contour_rects = []
    for i in range(1, section_cnt):
        x_low = int(width * ((i - 1) / section_cnt))
        x_high = int(width * (i / section_cnt))
        y_low = int(height * ((i - 1) / section_cnt))
        y_high = int(height * (i / section_cnt))
        rect = np.array(
            [
            (0, y_low),
            (width, y_low),
            (width, y_high),
            (0, y_high)
            ],
            dtype=np.int32
        ).reshape(-1,1,2)
        horizontal_contour_rects.append(rect)
        rect = np.array(
            [
            (x_low, 0),
            (x_high, 0),
            (x_high, height),
            (x_low, height)
            ],
            dtype=np.int32
        ).reshape(-1,1,2)
        vertical_contour_rects.append(rect)
    cv2.drawContours(img, horizontal_contour_rects if not direction else vertical_contour_rects, -1, (0, 0, 255), 8)
    cv2.imwrite(img_path[:-4] + "contours.png", img)
    return


def table_to_pdf() -> None:
    return

def crop_page(orig_page : pymupdf.Page, doc_title : str, element : str) -> None:
    # doc_path = convert_img_to_pdf(orig_page, "checkbox.png")
    # doc_name = "cropped_checkbox.pdf"
    # page = fitz.open(doc_path)[0]
    page_bounds = orig_page.bound()
    width = page_bounds.width
    height = page_bounds.height
    print(f"width: {width}, height: {height}")
    rect_bounds = []
    bounds = DOCUMENT_LAYOUT.get(doc_title, {}).get('bounds', [])
    for obj in bounds:
        if element in obj:
            b = obj.get(element, [])
            rect_bounds = [b[0][0] * width, b[0][1] * height, b[1][0] * width, b[1][1] * height]
            break
    rect = fitz.Rect(rect_bounds[0], rect_bounds[1], rect_bounds[2], rect_bounds[3])
    print(f"{rect=}")
    pix = orig_page.get_pixmap(clip=rect, dpi = 300)
    pix.save(f"cropped_{element}.png")
    return

def extract_values_from_image(page : pymupdf.Page) -> None:

    return

def convert_img_to_pdf(page : pymupdf.Page, name : str) -> Path:
    root_folder_path_obj = Path(__file__).parent
    image_output_folder_path_obj = root_folder_path_obj / "imgs"
    image_list = page.get_images()
    if not image_list:
        raise RuntimeError("Unable to locate images on a page")
    matrix = pymupdf.Matrix(4, 4)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    if pix.alpha:
        pix.set_alpha(None)
    # img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    # img = img.convert('L')
    # enhancer = ImageEnhance.Contrast(img)
    # img = enhancer.enhance(2)
    # enhancer = ImageEnhance.Sharpness(img)
    # img = enhancer.enhance(1.5)
    img_path = f"{image_output_folder_path_obj.absolute()}/n.png"
    pix.save(str(img_path)) #---- THIS INTERFERES WITH CHECKBOX DETECTION SOMEHOW
    # split_document_with_rectangular_contours(img_path, 40, 1)
    # img.save(img_path)
    # # remove_table_lines(img_path)
    # cfg = config.PipelinesConfig()
    # cfg.width_range = (30,55)
    # cfg.height_range = (25, 40)
    # cfg.scaling_factors = [0.7]
    # cfg.wh_ratio_range= (0.5, 1.7)
    # cfg.group_size_range = (2, 100)
    # cfg.dilation_iterations = 0
    # rects, grouping_rects, image, output_image = get_boxes(
    #     img_path, cfg=cfg, plot=False
    # )
    # checkboxes = get_checkboxes(
    #     img_path, cfg=cfg, px_threshold=0.1, plot=False, verbose=True
    # )
    # import matplotlib.pyplot as plt
    # for checkbox in checkboxes:
    #     print(f"Bounding rectangle: {checkbox[0]}")
    #     print(f"Result of 'constains_pixels' for the checkbox: {checkbox[1]}")
    #     plt.figure(figsize=(1,1))
    #     plt.imshow(checkbox[2])
    #     plt.show()
    # plt.figure(figsize=(20,20))
    # plt.imshow(output_image)
    # plt.show()
    # py_tess_result = pytesseract.image_to_string(img, lang="mkd", config=r'--oem 3 --psm 10 ')
    # print(f"{py_tess_result=}")
    doc_name = str(img_path)[:-3] + "pdf"
    pix.pdfocr_save(doc_name, language="mkd")
    return Path(doc_name)

def extract_content_from_page(page : pymupdf.Page) -> str:
    text = str(page.get_text("text", sort=True))
    text = re.sub('\n', '  ', text) #It is necessary to map it to more than just 1 space (2 or higher)
    # block = re.sub(r' {2,}', '\n', block)
    text = re.sub(r' {2,}', ' ', text)
    # block = re.sub(' +', '', block)
    # block = block.split("\n")
    return text

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
        # print(f"MATCHING expression: {struct.re_expression}")
        match = re.search(struct.re_expression.lower(), file_content.lower(), re.DOTALL)
        if match:
            result[struct.keyword] = match.group(1).strip()
            # print(f"{result=}")
        else:
            print("Entering modifier")
            match = re.search(struct.re_expression.lower(), file_content.lower(), re.DOTALL)
            if match:
                result[struct.keyword] = match.group(1).strip()
    # print(f"{matching_structs=}")
    print(f"{result=}")
    modify_customer_type_info(result)
    return result

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

def main():
    root_folder_path_obj = Path(__file__).parent
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
        doc_path = convert_img_to_pdf(doc[0], "a")
    if doc_path:
        doc = pymupdf.open(doc_path)
    crop_page(doc[0], "Договор за засновање претплатнички однос за користење", 'checkbox')
    crop_page(doc[0], "Договор за засновање претплатнички однос за користење", 'table')
    # pdf_content = extract_content_from_page(doc[0])
    # ocrHandler = OcrHandler(file_name.split(".")[0])
    # for bound in ocrHandler.bounds:
    #     print(bound.re_expression)
    # print(f"{pdf_content=}")
    # print(f"{match_expressions(ocrHandler.bounds, pdf_content)=}")
    return

if __name__ == "__main__":
    main()