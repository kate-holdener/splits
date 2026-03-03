from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from entity.runner import Runner
from entity.interval import Interval
from datetime import datetime
def generate_runner_report(runner: Runner, filename="runner_report.pdf"):
    if not runner.intervals:
        print(f"No intervals for {runner.name}. Report not generated.")
        return  # Exit early if no intervals

    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"Runner Report: {runner.name}")

    # Number of intervals
    num_intervals = len(runner.intervals)
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Number of intervals: {num_intervals}")

    y = height - 110
    total_distance = 0
    total_time = 0

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Interval")
    c.drawString(120, y, "Distance (m)")
    c.drawString(200, y, "Duration (s)")
    c.drawString(280, y, "Rest (s)")
    c.drawString(360, y, "Pace (s/m)")
    y -= 20


    # Date of the run (based on first interval start_time)
    first_start = runner.intervals[0].start_time
    run_date = datetime.fromtimestamp(first_start).strftime("%Y-%m-%d %H:%M:%S")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, f"Date: {run_date}")

    for i, interval in enumerate(runner.intervals):
        duration = interval.end_time - interval.start_time
        next_start = runner.intervals[i + 1].start_time if i + 1 < len(runner.intervals) else None
        rest = (next_start - interval.end_time) if next_start is not None else 0
        pace = duration / interval.distance if interval.distance != 0 else 0

        total_distance += interval.distance
        total_time += duration

        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"{i+1}")
        c.drawString(120, y, f"{interval.distance:.2f}")
        c.drawString(200, y, f"{duration:.2f}")
        c.drawString(280, y, f"{rest:.2f}")
        c.drawString(360, y, f"{pace:.2f}")

        prev_end = interval.end_time
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50

    # Average pace
    avg_pace = total_time / total_distance if total_distance != 0 else 0
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y-10, f"Average pace: {avg_pace:.2f} s/m")

    c.save()
    print(f"PDF report generated: {filename}")

