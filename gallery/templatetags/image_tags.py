from django import template

from core.images import responsive_srcset


register = template.Library()
register.filter('responsive_srcset', responsive_srcset)
