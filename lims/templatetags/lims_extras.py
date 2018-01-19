
from django.template import Library
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = Library()


@register.simple_tag
def pagination(view, page):
    """
    Generate the series of links to the pages in a paginated list.
    """
    paginator, page_num = page.paginator, page.number

    ON_EACH_SIDE = 3
    ON_ENDS = 2

    # If there are 10 or fewer pages, display links to every page.
    # Otherwise, do some fancy
    if paginator.num_pages <= 10:
        page_range = range(paginator.num_pages)
    else:
        # Insert "smart" pagination links, so that there are always ON_ENDS
        # links at either end of the list of pages, and there are always
        # ON_EACH_SIDE links at either end of the "current page" link.
        page_range = []
        if page_num > (ON_EACH_SIDE + ON_ENDS):
            page_range += [
                *range(0, ON_ENDS), '.',
                *range(page_num - ON_EACH_SIDE, page_num + 1),
            ]
        else:
            page_range.extend(range(0, page_num + 1))
        if page_num < (paginator.num_pages - ON_EACH_SIDE - ON_ENDS - 1):
            page_range += [
                *range(page_num + 1, page_num + ON_EACH_SIDE + 1), '.',
                *range(paginator.num_pages - ON_ENDS, paginator.num_pages)
            ]
        else:
            page_range.extend(range(page_num + 1, paginator.num_pages))

    links = []
    query_dict = view.request.GET.copy()

    for item in page_range:

        if item == ".":
            links.append("...")
            continue

        query_dict["page"] = item + 1
        page_num = item + 1

        if page_num == page.number:
            links.append(format_html('<span class="this-page">{}</span>', page_num))
        else:
            end = mark_safe(' class="end"') if item == paginator.num_pages - 1 else ''
            links.append(format_html('<a href="?{}"{}>{}</a>', query_dict.urlencode(), end, page_num))

    return mark_safe('<p class="paginator">%s</p>' % " ".join(links))
