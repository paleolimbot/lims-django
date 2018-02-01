
import re
import io
import base64

import qrcode

from django.utils.html import format_html


def qrcode_png(obj):

    qr = qrcode.QRCode(border=0)
    qr.add_data(obj.slug)
    # qr.make(fit=True)

    img = qr.make_image()

    with io.BytesIO() as out:
        img.save(out, format='png')
        return out.getvalue()


def qrcode_html(obj):
    png_data = qrcode_png(obj)

    # split label into a top and bottom to fit better...
    # default is to split after a date-like string
    label = obj.slug
    label_match = re.search(r'^(.*?_[0-9]{4}-[0-9]{2}-[0-9]{2})_(.*)$', label)
    if label_match:
        label_top = label_match.group(1)
        label_bottom = label_match.group(2)
    else:
        label_top = label[25:]
        label_bottom = label[25:]

    png_base64 = base64.encodebytes(png_data).decode('utf-8')

    html_format = '<div class="qrcode-full-label qrcode-full-label-medium">' \
                  '<div class="qrcode-label qrcode-label-top">{}</div>' \
                  '<img class="qrcode" src="data:image/png;base64,{}"/>' \
                  '<div class="qrcode-label qrcode-label-top">{}</div>' \
                  '</div>'

    return format_html(html_format, label_top, png_base64, label_bottom)
