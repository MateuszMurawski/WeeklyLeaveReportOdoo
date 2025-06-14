# ------------------------------------------------------------------------------------------------------------------------
# Author: Mateusz Murawski
# Date: 13.06.2025
# Report: Upcoming Remote Work and Absences
# ------------------------------------------------------------------------------------------------------------------------
# This script is executed as a server action in Odoo.
# It generates a tabular report of planned remote work and employee absences for the upcoming business days (excluding weekends).
# It retrieves data from the `hr.leave` model (only validated leave requests), generates an HTML table, and sends it via email to all active employees with an email address set in the "Employees" module.
# ------------------------------------------------------------------------------------------------------------------------

# Configuration
days_range = 8  # Number of days to include in the report (starting from today)
email_from = 'mail@odoo.pl'  # Sender's email address

# Calculate the date range and prepare workday lists
today = datetime.datetime.today().date()
last_day = today + datetime.timedelta(days=days_range-1)
start_date_str = today.strftime('%Y-%m-%d')
end_date_str = last_day.strftime('%Y-%m-%d')

# Day name translations (Polish)
translate_day_name = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela']

# Initialize data containers
working_days = []
day_name_list = []
day_date_list = []
employee_schedule = {}

# Collect working days (skip weekends)
for i in range(days_range):
    current_day = today + datetime.timedelta(days=i)
    if current_day.weekday() < 5:  # 0=Monday, 6=Sunday; skip weekends
        working_days.append(current_day)
        day_name_list.append(translate_day_name[current_day.weekday()])
        day_date_list.append(current_day.strftime('%d.%m.%Y'))

# Retrieve validated leave records that overlap with the selected date range
validated_leaves = env['hr.leave'].search([
    ('state', '=', 'validate'),
    ('request_date_from', '<=', end_date_str),
    ('request_date_to', '>=', start_date_str),
])

# Build employee schedule mapping
for leave_entry in validated_leaves:
    employee_name = leave_entry.employee_id.name.replace(' [ERP]', '').strip()
    
    if employee_name not in employee_schedule:
        # Initialize status for each working day
        employee_schedule[employee_name] = [{'am': None, 'pm': None} for _ in range(len(working_days))]
    
    for i, day in enumerate(working_days):
        if leave_entry.request_date_from <= day <= leave_entry.request_date_to:
            # Determine label: 'remote' or 'leave'
            label = 'remote' if leave_entry.holiday_status_id.name == 'Remote work' else 'leave'
    
            # Set half-day or full-day status
            if leave_entry.request_unit_half:
                employee_schedule[employee_name][i][leave_entry.request_date_from_period] = label
            else:
                employee_schedule[employee_name][i]['am'] = label
                employee_schedule[employee_name][i]['pm'] = label

# Sort employees alphabetically                
employee_schedule = dict(sorted(employee_schedule.items(), key=lambda x: x[0]))

# Email subject            
subject = f"📅 Praca zdalna i nieobcności zaplanowane na najbliższy tydzień ({today.strftime('%d.%m.%Y')} - {last_day.strftime('%d.%m.%Y')})"

# If no data, send a simple notification
if not employee_schedule :
    body = f"<h3>📅 Brak zaplanowanych nieobecności i pracy zdalnej na najbliższy tydzień ({today.strftime('%d.%m.%Y')} - {last_day.strftime('%d.%m.%Y')})</h3>"
else:
    # Build HTML report table
    body = '''
            <table style="border-collapse: collapse; text-align: center;">
                <tr>
                    <th rowspan="2" style="background-color: #d3d3d3; border: 1px solid black; padding: 5px;">Pracownik</th>
            '''
    
    # Add weekday names as headers      
    for i, name in enumerate(day_name_list):
        bg_color = 'background-color: #d3d3d3;' if i > 0 else 'background-color: #32d918'
        body += f'<th colspan="2" style="min-width: 110px; width: 110px; background-color: #d3d3d3; border: 1px solid black; padding: 5px; {bg_color}">{name}</th>'
    body += '</tr><tr>'
    
    # Add corresponding dates
    for i, date in enumerate(day_date_list):
        bg_color = 'background-color: #d3d3d3;' if i > 0 else 'background-color: #32d918'
        body += f'<th colspan="2" style="background-color: #d3d3d3; border: 1px solid black; padding: 5px; {bg_color}">{date}</th>'

    # Add employee rows
    for employee_name, status_list in employee_schedule.items():
        body += f'<tr><td style="height: 30px; min-height: 30px; background-color: #d3d3d3; border: 1px solid black; padding: 5px; text-align: left;">{employee_name}</td>'
        
        for day_status in status_list:
            am_status = day_status.get('am')
            pm_status = day_status.get('pm')
    
            if am_status == 'leave':
                am_style = 'background-color: #c34a4e; color: white;'
            elif am_status == 'remote':
                am_style = 'background-color: #67acd3; color: black;'
            else:
                am_style = ''
    
            if pm_status == 'leave':
                pm_style = 'background-color: #c34a4e; color: white;'
            elif pm_status == 'remote':
                pm_style = 'background-color: #67acd3; color: black;'
            else:
                pm_style = ''
    
            body += f'<td style="border: 1px solid black; border-right: none; {am_style}"></td>'
            body += f'<td style="border: 1px solid black; border-left: none; {pm_style}"></td>'
    
        body += '</tr>'
    
    # Add legend
    body += '''
            <tr>
                <td colspan="6" style="height: 40px;"></td>
            </tr>
            <tr>
                <td colspan="6" style="height: 40px;"></td>
            </tr>
            <tr>
                <th colspan="6" style="text-align: left; padding: 10px;"><h2>Legenda:<h2></th>
            </tr>
            <tr>
                <td></td>
                <td style="background-color: #c34a4e;"></td>
                <td style="background-color: #c34a4e;"></td>
                <td colspan="6" style="text-align: left; padding: 10px;">Nieobecność przez cały dzień</td>
            </tr>
            <tr>
                <td colspan="6" style="height: 1px;"></td>
            </tr>
            <tr>
                <td></td>
                <td style="background-color: #67acd3;"></td>
                <td style="background-color: #67acd3;"></td>
                <td colspan="6" style="text-align: left; padding: 10px;">Praca zdalna przez cały dzień</td>
            </tr>
            <tr>
                <td colspan="6" style="height: 1px;"></td>
            </tr>
            <tr>
                <td></td>
                <td></td>
                <td style="background-color: #c34a4e;"></td>
                <td colspan="10" style="text-align: left; padding: 10px;">Nieobecność w drugiej połowie dnia</td>
            </tr>
            <tr>
                <td colspan="6" style="height: 1px;"></td>
            </tr>
            <tr>
                <td></td>
                <td style="background-color: #c34a4e;"></td>
                <td style="background-color: #67acd3;"></td>
                <td colspan="10" style="text-align: left; padding: 10px;">Nieobecność w pierwszej połowie dnia, praca zdalna w drugiej</td>
            </tr>
        </table>
        '''

# Get all active employees with a work email
employees_records = env['hr.employee'].search([
    ('work_email', '!=', False),
    ('active', '=', True)
])

# Build list of recipient email addresses
email_list = [e.work_email for e in employees_records if e.work_email]
email_to = ','.join(email_list)

# Send the email
if email_to:
    env['mail.mail'].create({
        'subject': subject,
        'body_html': body,
        'email_to': email_to,
        'email_from': email_from,
    }).send()