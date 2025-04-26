
# def preprocess(data):
#     ""
#     title = data['title']
#     description = data["description"]
    
#     normalized_text = f'A product with {title} and {description}'

    
#     return normalized_text


    
def preprocess(data_point_dict):
    ""
    expected_features = ["title","description","price","category","brand"]
    normalized_string = "A product with "
    for feature in expected_features:
        if feature in data_point_dict:
            normalized_string += f"{feature} {data_point_dict[feature]} "
    return normalized_string.strip()