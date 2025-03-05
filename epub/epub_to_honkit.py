import ebooklib
from ebooklib import epub
import os
from bs4 import BeautifulSoup, NavigableString

def process_element(element):
    """
    Recursively processes a BeautifulSoup element and returns a Markdown string.
    Recognized elements:
      - <p class="part-title"> produces an H1.
      - <p class="top-int"> produces an H1.
      - <p class="top-int1"> produces an H2.
      - <p class="sec1-titlea"> produces an H2 header.
      - <p class="sec2-title"> produces an H3 header.
      - <li class="calibre14"> produces a bullet list item.
      - Other elements are processed based on their children.
    """
    md_text = ""

    # If element is a NavigableString, just return its stripped text.
    if isinstance(element, NavigableString):
        return element.strip()

    # Process <p> with class "part-title" as H1
    if element.name == "p" and "part-title" in (element.get("class") or []):
        text = element.get_text().strip()
        if text:
            md_text += f"# {text}\n\n"
        return md_text

    # Process <p> with class "top-int" as H1
    if element.name == "p" and "top-int" in (element.get("class") or []):
        text = element.get_text().strip()
        if text:
            md_text += f"# {text}\n\n"
        return md_text

    # Process <p> with class "top-int1" as H2
    if element.name == "p" and "top-int1" in (element.get("class") or []):
        text = element.get_text().strip()
        if text:
            md_text += f"## {text}\n\n"
        return md_text

    # Process <p> with class "sec1-titlea" as H2
    if element.name == "p" and "sec1-titlea" in (element.get("class") or []):
        text = element.get_text().strip()
        if text:
            md_text += f"## {text}\n\n"
        return md_text

    # Process <p> with class "sec2-title" as H3
    if element.name == "p" and "sec2-title" in (element.get("class") or []):
        text = element.get_text().strip()
        if text:
            md_text += f"### {text}\n\n"
        return md_text

    # Process list items: <li> with class "calibre14" as bullet items.
    if element.name == "li" and "calibre14" in (element.get("class") or []):
        text = element.get_text().strip()
        if text:
            md_text += f"- {text}\n"
        return md_text

    # If the element is a list container like <ul> or <ol>, process its children.
    if element.name in ["ul", "ol"]:
        for child in element.children:
            child_md = process_element(child)
            if child_md:
                md_text += child_md
        if md_text:
            md_text += "\n"
        return md_text

    # For container elements like <p>, <div>, <tbody>, <tr>, etc.,
    # process their children recursively.
    if element.name in ["p", "div", "table", "tbody", "tr"]:
        for child in element.children:
            md_text += process_element(child)
        # For paragraphs (that are not special headers), ensure proper spacing.
        if element.name == "p" and "part-title" not in (element.get("class") or []) and "top-int" not in (element.get("class") or []) and "top-int1" not in (element.get("class") or []) and "sec1-titlea" not in (element.get("class") or []) and "sec2-title" not in (element.get("class") or []):
            md_text = md_text.strip()
            if md_text:
                md_text += "\n\n"
        return md_text

    # Default: process children.
    for child in element.children:
        md_text += process_element(child)
    return md_text

def epub_to_honkit(epub_file):
    # Create a new directory for the Honkit project
    project_dir = os.path.splitext(os.path.basename(epub_file))[0]
    os.makedirs(project_dir, exist_ok=True)
    
    # Read the EPUB file
    book = epub.read_epub(epub_file)
    chapter_index = 0
    current_part_dir = None
    current_title_dir = None  # New variable for title containers.
    part_number = 0  # Initialize part number
    title_number = 0  # Initialize title number

    # Create lists to hold chapter titles and output directories for the master SUMMARY.md
    chapter_titles = []
    chapter_dirs = []  # store folder names (e.g., "title00", "part00")
    part_titles = []
    title_titles = []

    # Process each EPUB document item (HTML)
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find the <body> element; if not found, use the entire document.
            body = soup.find('body')
            if body is None:
                body = soup

            # Check for div with class "part" to create a new part directory.
            part_div = body.find("div", class_="part")
            if part_div:
                part_title_element = part_div.find("p", class_="part-title")
                if part_title_element:
                    part_title = part_title_element.get_text().strip()
                    part_titles.append(part_title)
                current_part_dir = os.path.join(project_dir, f'part{part_number:02d}')
                os.makedirs(current_part_dir, exist_ok=True)
                part_number += 1  # Increment part number for the next part
                # Reset current_title_dir when a new part is encountered.
                current_title_dir = None

            # Check for div with class "title" to create a new title directory.
            title_div = body.find("div", class_="title")
            if title_div:
                title_text = title_div.get_text().strip() or f"Title {title_number+1}"
                title_titles.append(title_text)
                current_title_dir = os.path.join(project_dir, f'title{title_number:02d}')
                os.makedirs(current_title_dir, exist_ok=True)
                title_number += 1

            # If no part directory was found, use the project directory.
            if current_part_dir is None:
                current_part_dir = project_dir

            # When writing out chapters, choose the directory:
            # prefer the current_title_dir if available; otherwise, use current_part_dir.
            output_dir = current_title_dir if current_title_dir is not None else current_part_dir

            # Extract chapter title from the <table class="title2">
            chapter_title = None
            table_title2 = body.find("table", class_="title2")
            if table_title2:
                td_top = table_title2.find("td", class_="top")
                if td_top:
                    chapter_number = table_title2.find("td", class_="bor1").get_text().strip()  # Extract chapter number
                    chapter_title_text = td_top.find("small")
                    if chapter_title_text:
                        chapter_title = chapter_title_text.get_text().strip()  # Extract chapter title
                    else:
                        chapter_title_text = td_top.get_text().strip()
                        chapter_title = chapter_title_text
                    if chapter_number:
                        chapter_title = f"{chapter_number}. {chapter_title}"
                    else:
                        chapter_title = chapter_title

            # Check for H1 title in the chapter content if chapter_title is still None
            if chapter_title is None:
                h1_title = body.find("p", class_="part-title")
                if h1_title:
                    chapter_title = h1_title.get_text().strip()
                else:
                    h1_title = body.find("p", class_="top-int")
                    if h1_title:
                        chapter_title = h1_title.get_text().strip()
                    else:
                        h1_title = body.find("p", class_="top-int1")
                        if h1_title:
                            chapter_title = h1_title.get_text().strip()
                        else:
                            h1_title = body.find("p", class_="sec1-titlea")
                            if h1_title:
                                chapter_title = h1_title.get_text().strip()
                            else:
                                h1_title = body.find("p", class_="sec2-title")
                                if h1_title:
                                    chapter_title = h1_title.get_text().strip()
                                else:
                                    h1_title = body.find("p", class_="top1")  # Added this line
                                    if h1_title:
                                        chapter_title = h1_title.get_text().strip()
                                    else:
                                        # If no chapter title was found, use a default title.
                                        chapter_title = f"Chapter {chapter_index+1}"

            # Check if a chapter with the same title already exists.
            existing_chapter = False
            for i, title in enumerate(chapter_titles):
                if title == chapter_title:
                    existing_chapter = True
                    chapter_index = i
                    break

            if existing_chapter:
                continue

            # Build the Markdown content.
            md_content = f"# {chapter_title}\n\n"

            # Remove the duplicated H1 title from the chapter content.
            table_title2 = body.find("table", class_="title2")
            if table_title2:
                table_title2.decompose()

            # Process the body for subtitles and other content.
            md_content += process_element(body)

            # Write the chapter content under the chosen directory.
            chapter_md_file = os.path.join(output_dir, f'chapter{chapter_index:02d}.md')
            with open(chapter_md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)

            # Record chapter title and the directory (by its basename) for SUMMARY.md
            chapter_titles.append(chapter_title)
            chapter_dirs.append(os.path.basename(output_dir))
            chapter_index += 1
    
    # Create a master SUMMARY.md file at the project root.
    master_summary_file = os.path.join(project_dir, 'SUMMARY.md')
    with open(master_summary_file, 'w', encoding='utf-8') as f:
        f.write("# Summary\n\n")
        f.write("- [简介](README.md)\n")
        f.write("- [关于](gitbook/README.md)\n\n")
        f.write("## Content\n\n")
        for i, title in enumerate(chapter_titles):
            folder = chapter_dirs[i]
            f.write(f"- [{title}](gitbook/markdown/zh/{folder}/chapter{i:02d}.md)\n")

def main():
    epub_file = input("Please enter the path to the EPUB file: ")
    if not os.path.exists(epub_file):
        print("The file does not exist.")
        return
    if not epub_file.endswith('.epub'):
        print("The file is not an EPUB file.")
        return
    epub_to_honkit(epub_file)
    print("Conversion complete.")

if __name__ == "__main__":
    main()
