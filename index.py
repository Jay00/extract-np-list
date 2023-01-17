import json
import io
from datetime import datetime
import email
import base64
from typing import IO
import boto3
from pytz import timezone

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBoxHorizontal
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage


def MineNoPaperList(pdfData: IO) -> str:

    # document = open('2019-03-12_calendar.pdf', 'rb')
    document = pdfData
    # Create resource manager
    rsrcmgr = PDFResourceManager()
    # Set parameters for analysis.
    laparams = LAParams(line_overlap=0.5,  # Default 0.5
                        char_margin=0.5,  # Default 2.0
                        line_margin=0.5,  # Default 0.5
                        word_margin=0.0,  # Default 0.1
                        boxes_flow=0.5,  # Default 0.5
                        detect_vertical=False,  # Default False
                        all_texts=False)  # Default False

    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    calendar_date: str = ""  # Will be string yyyy-mm-dd
    calendar_time: str = ""  # Will be string, 04:00 PM

    for page in PDFPage.get_pages(document):
        interpreter.process_page(page)
        # receive the LTPage object for the page.
        layout = device.get_result()
        # print("Layout: " + str(layout.pageid))  # Actual Page ID, 1 based
        # print("Page: " + str(page.pageid))
        page_num = layout.pageid

      

        for element in layout:
            # print(element)
            # Only use LTTextBoxHorizontal Elements
            if isinstance(element, LTTextBoxHorizontal):
                #     print(element.get_text())
                bbox = element.bbox
                text = element.get_text()

                # print(
                #     f"0:{bbox[0]}, 1:{bbox[1]}, 2:{bbox[2]}, 3:{bbox[3]}, {text}")

                # x0: the distance from the left of the page to the left edge of the box.
                # y0: the distance from the bottom of the page to the lower edge of the box.
                # x1: the distance from the left of the page to the right edge of the box.
                # y1: the distance from the bottom of the page to the upper edge of the box.

                # If this is the first page, check for Date and Time Value
                if page_num == 1:
                    SUPER_HEADER = 560  # Above this value is the date and time of the No Paper list
                    if (bbox[1] > SUPER_HEADER):

                        # Calendar Date: 01/10/2023
                        if (bbox[0] > 70) and (bbox[0] < 90):
                            # print(f"Calendar Date is {text}")
                            d = text.strip()
                            month = d[0:2]
                            day = d[3:5]
                            year = d[6:]
                            calendar_date = f"{year}-{month}-{day}"
                            print(f"Calendar Date is {calendar_date}")

                        # Time: 04:00 PM
                        if (bbox[0] > 620) and (bbox[0] < 650):
                            # print(f"Time Printed is: {text}")
                            calendar_time = text.strip()
                            print(f"Time Printed is: {calendar_time}")
                        

                        # with open("header.txt", "a") as file1:
                        #     # Writing data to a file
                        #     file1.write(f"{bbox} - {text}\n")

        break # Stop after first page

    # with open("myfile.txt", "w") as file1:
    #     # Writing data to a file
    #     for r in final_rows:
    #         file1.write(f"{r.__repr__()}\n")

    
    date_string = f"{calendar_date} {calendar_time}"  # 01/10/2023 04:00 PM
    

    return date_string

def handlePDFAttachment(pdf: IO):
    
    date_string = MineNoPaperList(pdf) # 01/10/2023 04:00 PM
    t = datetime.strptime(date_string, "%Y-%m-%d %I:%M %p")
    eastern = timezone("US/Eastern")
    awareDate = eastern.localize(t)

    file_key = awareDate.strftime("%Y-%m-%d-%H-%M.pdf")

    s3 = boto3.client('s3')
    pdf.seek(0)
    
    s3.upload_fileobj(pdf, 'court-dc-no-paper-lists', file_key)


def handler(event, context):
    # print("Event", event)

    record = event['Records'][0]
    # print("Record found.", type(record))

    sns = record['Sns']
    # print("Sns Found.", type(sns))

    message = sns["Message"]
    # print("Message", type(message))

    # print("Attempting to convert message to json")
    msgjson = json.loads(message)

    print("\n\nAttempting to retrieve email contents...")
    contents = msgjson['content']
    # print("Contents", type(contents), contents)

    # Contents are the email Base64 encoded
    # decoded = base64.b64decode(contents.encode("utf8")).decode("utf8")
    decoded = base64.b64decode(contents.encode("utf8"))
    print("Email Contents Decoded")

    # Extract PDF attachment
    # Given the s3 object content is the ses email, get the message content and attachment using email package
    # msg = email.message_from_string(decoded)
    msg = email.message_from_bytes(decoded)
    print("MSG", type(msg))

    for part in msg.walk():

        # print(f"Type: {part.get_content_type()}")
        # print(f"MainType: {part.get_content_maintype()}")
        # print(f"Subtype: {part.get_content_subtype()}")
        # print(f"Disposition: {part.get_content_disposition()}")
        # print(f"Boundary: {part.get_boundary()}")
        # print(f"Filename: {part.get_filename()}")

        if part.get_content_subtype() == "pdf":
            data = part.get_payload(decode=True)
            # print("Data Type", type(data))
            pdf = io.BytesIO(data)
            handlePDFAttachment(pdf)

    print("Finished Processing")

    return {'statusCode': 200,
            # 'body': json.dumps(data),
            'headers': {'Content-Type': 'application/json'}}

if __name__ == '__main__':

    document = open(f"attachment.pdf", 'rb')
    final_rows = handlePDFAttachment(document)
