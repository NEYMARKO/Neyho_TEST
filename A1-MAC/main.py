import re
import cv2
import fitz
import pymupdf
import numpy as np
from enum import Enum
from pathlib import Path
from boxdetect import config
from itertools import product
from boxdetect.pipelines import get_checkboxes
from table_content_extractor import TableExtractor

regs = {'3': [
    r'бр\.\s*(\d+)',
    r'на ден\s+(\b[0-9\.]*\b)\s+помеѓу',
    r'(?<=ПРЕТПЛАТНИК)(.*)(?=правно лице)',
    r'ЕМБГ:\s+(\b[0-9]+\b)'
    ]}

class DocType(Enum):
    TYPE_1 = 1
    TYPE_2 = 2
    TYPE_3 = 3
    TYPE_4 = 4
    TYPE_5 = 5
    UNDEFINED = -1

DOC_NAME_TO_TYPE_MAP = {
    "Договор за засновање претплатнички однос за користење": DocType.TYPE_1,
    "Договор за купопродажба на уреди со одложено плаќање на рати": DocType.TYPE_2,
    "Договор за користење на јавни комуникациски услуги": DocType.TYPE_3,
    "Договор за користење на јавни комуникациски услуги ---- CHANGE MEEEEEE": DocType.TYPE_4,
    "БАРАЊЕ ЗА ПРЕНЕСУВАЊЕ НА УСЛУГИ ПОМЕЃУ РАЗЛИЧНИ БАН БРОЕВИ КОИ ПРИПАЃААТ НА ИСТ ПРЕТПЛАТНИК": DocType.TYPE_5
}

DOCUMENT_LAYOUT = {
    DocType.TYPE_1:
    {
        'bounds':
        [
            {
                'table': [

                ],
                'checbox': [

                ]
            }
        ]
    },
    DocType.TYPE_2:
    {
        'bounds':
        [
            {
                'table': [

                ],
                'checbox': [
                    
                ]
            }
        ]
    },
    DocType.TYPE_3: 
    {
        'bounds': 
        [
            {
                'table': [
                    (0.075, 0.185),
                    (0.925, 0.265)
                ]
            },
            {
                'checkbox': [
                    (0.225, 0.175),
                    (0.6, 0.21)
                ]
            }
        ]
    },
    DocType.TYPE_4: 
    {
        'bounds': 
        [
            {
                'table': [
                    (0.075, 0.185),
                    (0.925, 0.265)
                ]
            },
            {
                'checkbox': [
                    (0.225, 0.175),
                    (0.6, 0.21)
                ]
            }
        ]
    },
    DocType.TYPE_5: 
    {
        'bounds': 
        [
            {
                'table': [
                    
                ]
            },
            {
                'checkbox': [
                    (0.225, 0.15),
                    (0.6, 0.2)
                ]
            }
        ]
    }
}

def generate_all_date_regex_combinations() -> list[tuple[str]]:
    denumerators = [".", ",", "-"]
    size = 2
    date_regexes = []
    cartesian_product = list(product(denumerators, repeat=size))
    # print(f"{cartesian_product=}")
    for prod in cartesian_product:
        date_regexes.append("\\d{2}" + f"\\{prod[0]}" + "\\d{2}" + f"\\{prod[1]}" + "\\d{2,4}")
    return date_regexes

DATE_REGEXES = generate_all_date_regex_combinations()

DOCUMENT_REGEXES = {
    DocType.TYPE_3: 
    {
        "BAN": "комуникациски услуги бр\\.\\s(\\d+)",
        "contract_date": DATE_REGEXES,
        "customer_type": "(?<=ПРЕТПЛАТНИК).*?(?=Име и презиме)" ,
        "EMBG_EDB": "ЕМБГ\\:\\s(\\d{13})"
    }
}

class VisualDebugger:
    def __init__(self):
        return
    def plot_img(self):
        return
    def draw_img(self):
        return

    def split_document_with_rectangular_contours(self, img_path : str, section_cnt : int, direction : int = 0) -> None:
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

def extract_content_from_page(page : pymupdf.Page) -> str:
    text = str(page.get_text("text", sort=True))
    text = re.sub('\n', '  ', text) #It is necessary to map it to more than just 1 space (2 or higher)
    text = re.sub(r' {2,}', ' ', text)
    # print(f"{text=}")
    return text

def crop_page(orig_page : pymupdf.Page, doc_type : DocType, element : str) -> Path:
    """
    Crops page using hardcoded bound values for given element and saves result to png.
    """
    page_bounds = orig_page.bound()
    width = page_bounds.width
    height = page_bounds.height
    rect_bounds = []
    bounds = DOCUMENT_LAYOUT.get(doc_type, {}).get('bounds', [])
    for obj in bounds:
        if element in obj:
            b = obj.get(element, [])
            rect_bounds = [b[0][0] * width, b[0][1] * height, b[1][0] * width, b[1][1] * height]
            break
    rect = fitz.Rect(rect_bounds[0], rect_bounds[1], rect_bounds[2], rect_bounds[3])
    pix = orig_page.get_pixmap(clip=rect, dpi = 300)
    img_path = Path().resolve() / f"cropped_{element}.png"
    pix.save(img_path)
    return img_path

def raw_img_to_pdf(img_src : Path, dest_folder : Path, file_name : str) -> pymupdf.Document:
    doc = fitz.open()
    imgdoc = fitz.open(str(img_src))
    pdfbytes = imgdoc.convert_to_pdf()
    imgpdf = fitz.open("pdf", pdfbytes)
    doc.insert_pdf(imgpdf)
    if not dest_folder.exists() and not dest_folder.is_dir():
        dest_folder.mkdir(parents=True, exist_ok=True)
    doc.save(str(dest_folder / file_name))
    return scanned_img_to_pdf(doc[0], dest_folder, file_name)

def scanned_img_to_pdf(page : pymupdf.Page, dest_folder : Path, file_name : str) -> pymupdf.Document:
    image_list = page.get_images()
    if not image_list:
        raise RuntimeError("Unable to locate images on a page")
    matrix = pymupdf.Matrix(4, 4)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    if pix.alpha:
        pix.set_alpha(None)
    # pix.save(str(dest))
    if not dest_folder.exists() and not dest_folder.is_dir():
        dest_folder.mkdir(parents=True, exist_ok=True)
    doc_path = str(dest_folder / file_name)
    pix.pdfocr_save(doc_path, language="mkd")
    return pymupdf.open(str(doc_path))

def get_checkbox_content(page : pymupdf.Page, doc_type : DocType) -> dict[str, bool]:
    """
    In case of not detecting checkboxes, check width and height range of
    checkboxes in image -> can use any image viewer => good one: https://pixspy.com/ 
    """
    img_path = str(crop_page(page, doc_type, 'checkbox').absolute())
    cfg = config.PipelinesConfig()
    cfg.width_range = (90, 200)      # Adjust based on actual checkbox size
    cfg.height_range = (70, 200)     # Should be similar to width for square boxes
    cfg.scaling_factors = [0.7, 0.8, 0.9, 1.0, 1.1]
    cfg.wh_ratio_range = (0.8, 1.2)  # Closer to square
    cfg.group_size_range = (1, 5)
    cfg.dilation_iterations = [0]      # Start with 1, try 2 if needed
    
    checkboxes = get_checkboxes(
        img_path, cfg=cfg, px_threshold=0.1, plot=False, verbose=False
    )

    if checkboxes.size == 0:
        print("Unable to detect checkboxes, check cfg.width and height range")
        return {}
    
    #sort using x coordinate => let checboxes go from left to right
    sorted_checkboxes = sorted(checkboxes.tolist(), key=lambda inner_l: inner_l[0][0], reverse=False)
    is_resident = sorted_checkboxes[0][1]
    return {"customer_type_resident" : is_resident, "customer_type_bussiness" : not is_resident}

def get_table_content(page : pymupdf.Page, doc_type : DocType, file_basename : str) -> str:
    img_path = crop_page(page, doc_type, 'table')
    tableExtractor = TableExtractor(img_path)
    tableExtractor.clear_table()
    doc = raw_img_to_pdf(tableExtractor.result_path, Path(__file__).parent / "raw_img_to_pdf" / file_basename, "raw_img.pdf")
    return extract_content_from_page(doc[0])

def get_date(file_content : str) -> str:
    date_string = ""
    for date_format in DATE_REGEXES:
        match = re.search(date_format, file_content, re.DOTALL)
        # print(f"{match=}")
        if match:
            date_string = match.group(0).strip()
            break
    if ',' in date_string:
        date_string = date_string.replace(',', '.')
    if '-' in date_string:
        date_string = date_string.replace('-', '.')
    return date_string

def get_number(digit_cnt_low : int, digit_cnt_high : int, content : str) -> str:
    expression = "\\s\\d{" + str(digit_cnt_low) + "," + str(digit_cnt_high) + "}\\s"
    # print(f"{expression=}")
    match = re.search(expression, content, re.DOTALL)
    # print(f"CONTENT TO MATCH: {content}")
    if match:
        # print(f"Number match: {match}")
        return match.group(0).strip()
    return ""

#USED FOR OCR (FOR NOW)
def extract_all_relevant_data(doc : pymupdf.Document, doc_type : DocType, file_basename : str) -> dict:
    checkbox_content = get_checkbox_content(doc[0], doc_type)
    print(f"{checkbox_content=}")
    table_content = get_table_content(doc[0], doc_type, file_basename)
    print(f"{table_content=}")
    date = get_date(extract_content_from_page(doc[0]))
    ban = get_number(9, 10, extract_content_from_page(doc[0]))
    embg_edb = get_number(8, 14, table_content)
    result = {"BAN": ban, "contract_date": date, "EMBG_EDB": embg_edb}
    result.update(checkbox_content)
    return result

#USED FOR REGULAR PDF (FOR NOW)
def extract_data(doc : pymupdf.Document, doc_type : DocType) -> dict:
    content = extract_content_from_page(doc[0])
    result = {}
    for expression in DOCUMENT_REGEXES.get(doc_type, {}).get("contract_date", []):
        match = re.search(expression, content, re.DOTALL)
        if match:
            result["contract_date"] = match.group(1)
    ban_match = re.search(DOCUMENT_REGEXES.get(doc_type, {}).get("BAN", ""), content, re.DOTALL)
    if ban_match:
        result["BAN"] = ban_match.group(1)
    embg_edb_match = re.search(DOCUMENT_REGEXES.get(doc_type, {}).get("EMBG_EDB", ""), content, re.DOTALL)
    if embg_edb_match:
        result["EMBG_EDB"] = embg_edb_match.group(1)
    customer_type_match = re.search(DOCUMENT_REGEXES.get(doc_type, {}).get("customer_type", ""), content, re.DOTALL)
    if customer_type_match:
        matched_string = customer_type_match.group(0).strip().lower()
        print(f"{matched_string=}")
        is_resident = False
        possible_check_marks = [chr(0x455), chr(0x78)]
        all_mark_positions = [matched_string.find(possible_check_marks[i]) for i in range(len(possible_check_marks))]
        print(f"{all_mark_positions=}")
        if all(var == -1 for var in all_mark_positions):
            raise ValueError("Unable to detect checked box")
        is_resident = any(var == 0 for var in all_mark_positions)
        result["customer_type_resident"] = is_resident
        result["customer_type_businness"] = not is_resident
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
    root_folder_path_obj = Path(__file__).parent / "INPUT/TYPE_3"
    file_basename = ""
    file_name_with_extension = ""
    for x in root_folder_path_obj.iterdir():
        if x.is_file() and x.name.endswith("pdf"):
            print(f"{"-" * 40}Processing file: {x.stem}{"-" * 40}")
            file_basename = x.stem
            file_name_with_extension = x.name
            # doc_type = DOC_NAME_TO_TYPE_MAP.get(file_basename, DocType.UNDEFINED)
            doc_type = DocType.TYPE_3
            doc = pymupdf.open(Path(root_folder_path_obj / file_name_with_extension))
            result = None
            if not is_regular_pdf_page(doc[0]):
                doc = scanned_img_to_pdf(doc[0], Path(__file__).parent / "scanned_img_to_pdf" / file_basename, "scanned_img.pdf")
                result = extract_all_relevant_data(doc, doc_type, file_basename) 
            else:
                result = extract_data(doc, doc_type)
            if not doc:
                raise RuntimeError("Unable to read document!")
            # result = extract_all_relevant_data(doc) 
            print(f"{result=}")
    return

if __name__ == "__main__":
    main()