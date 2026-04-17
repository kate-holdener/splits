from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime


def _format_duration(ms: float) -> str:
    """Format milliseconds as M:SS.ss (e.g. '2:03.50')."""
    total_seconds = ms / 1000.0
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:05.2f}"


def _format_pace(total_ms: float, total_distance_m: float) -> str:
    """Return average pace as M:SS.ss per 1600 m."""
    if total_distance_m == 0:
        return "N/A"
    pace_sec_per_1600m = (total_ms / 1000.0) / total_distance_m * 1600
    minutes = int(pace_sec_per_1600m // 60)
    seconds = pace_sec_per_1600m % 60
    return f"{minutes}:{seconds:05.2f}"


def generate_runner_report(runner, filename: str = "runner_report.pdf"):
    """
    Generate a PDF performance report for one athlete.

    ``runner`` may be either:
    - A Runner entity object  (has .intervals, .current_workout, .name, .lname)
    - A session dict          (keys: 'session_intervals', 'workout', 'name', 'lname')
    """
    # ------------------------------------------------------------------ #
    # Normalise input so the rest of the function works with plain values #
    # ------------------------------------------------------------------ #
    if isinstance(runner, dict):
        name = runner.get('name', '')
        lname = runner.get('lname', '')
        workout_data = runner.get('workout') or {}
        interval_distance = workout_data.get('interval_distance', 0)
        configured_rest = workout_data.get('rest_time', 0)
        date_str = workout_data.get('date_and_time', '')
        try:
            workout_date = datetime.fromisoformat(date_str).strftime("%B %d, %Y  %H:%M")
        except Exception:
            workout_date = date_str or "Unknown"

        completed = [
            iv for iv in runner.get('session_intervals', [])
            if not iv.get('incomplete', True)
        ]
        # list of (start_ms, end_ms, distance_m)
        interval_list = [(iv['start_time'], iv['end_time'], iv['distance'])
                         for iv in completed]
    else:
        # Runner entity
        name = runner.name or ''
        lname = getattr(runner, 'lname', '') or ''
        workout = runner.current_workout
        interval_distance = workout.interval_distance if workout else 0
        configured_rest = workout.rest_time if workout else 0
        if workout and workout.date_and_time:
            workout_date = workout.date_and_time.strftime("%B %d, %Y  %H:%M")
        else:
            workout_date = "Unknown"

        completed = [iv for iv in runner.intervals if not iv.incomplete]
        interval_list = [(iv.start_time, iv.end_time, iv.distance)
                         for iv in completed]

    if not interval_list:
        print(f"No completed intervals for {name} {lname}. Report not generated.")
        return

    # ------------------------------------------------------------------ #
    # Build PDF                                                            #
    # ------------------------------------------------------------------ #
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=inch, rightMargin=inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        'ReportTitle', parent=styles['Title'], fontSize=20, spaceAfter=4
    )
    story.append(Paragraph("Interval Training Report", title_style))

    # Athlete name
    name_style = ParagraphStyle(
        'AthleteName', parent=styles['Heading2'], fontSize=15, spaceAfter=6
    )
    full_name = f"{name} {lname}".strip()
    story.append(Paragraph(full_name, name_style))

    story.append(Spacer(1, 0.12 * inch))

    # Workout details
    normal = styles['Normal']
    story.append(Paragraph(f"<b>Date:</b> {workout_date}", normal))
    story.append(Paragraph(f"<b>Interval Distance:</b> {interval_distance} m", normal))
    story.append(Paragraph(
        f"<b>Configured Rest Time:</b> {configured_rest} s", normal
    ))
    story.append(Paragraph(
        f"<b>Completed Intervals:</b> {len(interval_list)}", normal
    ))

    story.append(Spacer(1, 0.2 * inch))

    # ------------------------------------------------------------------ #
    # Interval table                                                       #
    # ------------------------------------------------------------------ #
    header = ["#", "Interval Time", "Rest After"]
    table_data = [header]

    total_ms = 0.0
    total_distance = 0.0

    for i, (start_ms, end_ms, distance) in enumerate(interval_list):
        duration_ms = end_ms - start_ms
        total_ms += duration_ms
        total_distance += distance

        if i + 1 < len(interval_list):
            next_start = interval_list[i + 1][0]
            rest_str = _format_duration(next_start - end_ms)
        else:
            rest_str = "—"

        table_data.append([
            str(i + 1),
            _format_duration(duration_ms),
            rest_str,
        ])

    col_widths = [0.6 * inch, 2.0 * inch, 2.0 * inch]
    t = Table(table_data, colWidths=col_widths)

    style_cmds = [
        ('BACKGROUND',   (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR',    (0, 0), (-1, 0), colors.white),
        ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, -1), 11),
        ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME',     (0, 1), (-1, -1), 'Helvetica'),
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING',   (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
    ]
    # Alternating row shading
    for row_idx in range(1, len(table_data)):
        if row_idx % 2 == 0:
            style_cmds.append(
                ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#f2f2f2'))
            )

    t.setStyle(TableStyle(style_cmds))
    story.append(t)

    story.append(Spacer(1, 0.25 * inch))

    # Average pace
    avg_pace = _format_pace(total_ms, total_distance)
    pace_style = ParagraphStyle(
        'PaceLine', parent=styles['Normal'], fontSize=13
    )
    story.append(Paragraph(
        f"<b>Average Pace:</b> {avg_pace} min / 1600 m", pace_style
    ))

    doc.build(story)
    print(f"PDF report generated: {filename}")
