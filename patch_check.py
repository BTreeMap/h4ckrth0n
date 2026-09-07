with open("scripts/check_doc_routes.py", "r") as f:
    text = f.read()
text = text.replace("for method in path_item.keys():", "for method in path_item:")
with open("scripts/check_doc_routes.py", "w") as f:
    f.write(text)
