import re
f = open(r'C:\Users\AnilKondaveni\Downloads\techcarrotOdoo 6\techcarrotOdoo-Staging\employee_profile_change_request\views\hr_profile_change_request_views.xml', encoding='utf-8')
c = f.read()
f.close()
old = 'parent="' + '[hr.menu](http://hr.menu)' + '_hr_root"'
new = 'parent="hr.' + 'menu_hr_root"'
c = c.replace(old, new)
f = open(r'C:\Users\AnilKondaveni\Downloads\techcarrotOdoo 6\techcarrotOdoo-Staging\employee_profile_change_request\views\hr_profile_change_request_views.xml', 'w', encoding='utf-8')
f.write(c)
f.close()
print('Done - fixed!')
