

while True:
    column_index = 0
    user_input = input("Enter column index (q for quitting): ")
    try:
        column_index = int(user_input)
    except:
        if user_input == "q":
            break
        else:
            print("invalid argument")
    column_code = ""
    number = ""
    if column_index // 26 == 0:
        column_code = chr(65 + column_index % 26)

    else:
        while column_index != 0:
            print(f"{column_index=}")
            a = column_index % 26
            number += str(a)
            column_index //= 26
            column_code += chr(65 + a) if column_index != 0 else chr(65 + a - 1)
        if column_index != 0:
            column_code += chr(65 + column_index)
    print(column_code[::-1])


