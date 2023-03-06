from xhtml2pdf import pisa
from django.template.loader import get_template


def generate_electric_panel_schedule(building_id, response):
    """
    Generate Electric Panel Schedule
        Parameters:
            building_id (str): building_id to get the electric panel schedule of.
            response (object): HTTP Response Object.

    """
    template_file = "generate_panel_report.html"

    template = get_template(template_file)

    # TODO: Get panel and circuit data from database

    panel_data = {"panels": ["panel_1", "panel_2"]}
    source_html = template.render(panel_data)

    # Handover to pisa to do conversion
    pisa.showLogging()
    return convert_html_to_pdf(source_html, response)


# Utility function
def convert_html_to_pdf(source_html, response):
    # convert HTML to PDF
    pisa_status = pisa.CreatePDF(
        src=source_html,  # the HTML to convert
        dest=response)  # file handle to receive result

    # return True on success and False on errors
    return response
