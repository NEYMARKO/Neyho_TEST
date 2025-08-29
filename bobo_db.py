import json
import sys
import io
import os

import eywa
import asyncio

sys.path.insert(1, r"C:\Users\Marko\Desktop\Neyho\Neyho_TEST")
if os.name == 'posix':  # (macOS, Linux)
    sys.path.insert(1, os.path.join("..", ".."))

    INPUT_DIR = os.path.join(os.path.expanduser("~"), 'json_input')

elif os.name == 'nt':  # Windows
    #root directory
    sys.path.insert(1, r"C:\Users\Marko\Desktop\Neyho\Neyho_TEST")

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    INPUT_DIR = os.path.join(SCRIPT_DIR, "json_input")

# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
INPUT_FILE = "input.json"

def get_input(input_dir, input_file):
    try:
        with open(os.path.join(input_dir, input_file), 'r', encoding='utf-8') as f:
            input_data = json.load(f)
            return input_data
    except:
        print(f'Failed to read {input_file} from {input_dir}.')

def format_ocr_doc_to_obj(input_obj):
    return {
        'document_type' : input_obj.get('document_type'),
        'extraction_timestamp' : input_obj.get('extraction_timestamp'),
        'source_format': input_obj.get('source_format'),
        'source_file': input_obj.get('source_file')
    }

def extract_data_from_metadata(metadata_obj):
    return {
        'confidence_score': metadata_obj.get('confidence_score'),
        'extracted_text_sample': metadata_obj.get('extracted_text_sample')
    }

def get_document_data_through_relation(input_obj):
    result = format_ocr_doc_to_obj(input_obj)
    vendor_data_input = input_obj.get('vendor')
    customer_data_input = input_obj.get('customer')
    result['vendor'] = vendor_data_input
    result['customer'] = customer_data_input
    return result

def get_totals_data_through_relation(input_obj):
    totals = input_obj.get('totals')
    tax_breakdown = totals.get('tax_breakdown')
    if 'tax_breakdown' in totals:
        del totals['tax_breakdown']
    totals['tax_breakdowns'] = tax_breakdown
    # print(f"{tax_breakdown=}")
    return totals

def format_string_list_to_obj_list(string_list, attribute_name):
    result = []
    for string in string_list:
        result.append({f'{attribute_name}' : string})
    return result

def get_metadata_through_relation(input_obj):
    temp_metadata = input_obj.get('metadata')
    metadata_input = extract_data_from_metadata(temp_metadata)
    metadata_input['processing_notes'] = format_string_list_to_obj_list(temp_metadata.get('processing_notes'), 'note')
    metadata_input['warnings'] = format_string_list_to_obj_list(temp_metadata.get('warnings'), 'warning')
    return metadata_input

def construct_sending_data_obj(input_obj):
    invoice_details = input_obj.get('invoice_details', {})
    # print(f"{invoice_details=}")
    line_items = input_obj.get('line_items')

    # print(f"{input_obj.get('totals').get('tax_breakdown')}")
    return {
        'invoice_number': invoice_details.get('invoice_number'),
        'invoice_date': invoice_details.get('invoice_date'),
        'due_date': invoice_details.get('due_date'),
        'order_number': invoice_details.get('order_number'),
        'order_date': invoice_details.get('order_date'),
        'delivery_date': invoice_details.get('delivery_date'),
        'payment_terms': invoice_details.get('payment_terms'),
        'currency': invoice_details.get('currency'),
        'document': get_document_data_through_relation(input_obj),
        'line_items': line_items,
        'totals': get_totals_data_through_relation(input_obj),
        'metadata': get_metadata_through_relation(input_obj)
    }
async def send_data_to_db(data_obj):
    print("SENDING")
    return await eywa.graphql("""
    mutation($bp_data : InvoiceDetailsInput!)
    {
        stackInvoiceDetails(data : $bp_data)
        {
            euuid
            
        }
    }
    """, {"bp_data" : data_obj})


def write_to_json_file(data: dict, relative_path: str) -> None:
    """
    Writes provided data to json file in location provided by relative_path (path is relative to bobo_db.py file location)
    """
    json_str = json.dumps(data, indent=4, ensure_ascii=False)
    with open(fr'{os.path.dirname(os.path.abspath(__file__))}\{relative_path}', "w", encoding="utf-8") as f:
        f.write(json_str)


async def main():
    eywa.open_pipe()
    input = get_input(INPUT_DIR, INPUT_FILE)
    sending_data = construct_sending_data_obj(input)
    write_to_json_file(sending_data, r"json_output\sample.json")
    try:
        await send_data_to_db(sending_data)
        print("SUCCESSFULLY SENT DATA")
    except:
        print("FAILED TO SEND DATA")
    eywa.exit()
    return


if __name__ == "__main__":
    asyncio.run(main())