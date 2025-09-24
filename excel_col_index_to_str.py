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

    while column_index > 0:
        column_index-=1
        a = column_index % 26
        column_index //= 26
        column_code += chr(65 + a)
    print(column_code[::-1])
