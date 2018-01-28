
import qrcode
import io
import base64


def qrcode_png(obj):
    class_name = type(obj).__name__
    img = qrcode.make('%s:%s' % (class_name, obj.slug))

    with io.BytesIO() as out:
        img.save(out, format='png')
        return out.getvalue()


def qrcode_html(obj):
    png_data = qrcode_png(obj)
    return '<img class="qrcode" src="data:image/png;base64,%s"/>' % base64.encodebytes(png_data).decode('utf-8')