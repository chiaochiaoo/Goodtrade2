import requests



#### MOVE THESE TO EMS ### 




def get_current_positions(user):

    try:
        d = {}
        p="http://127.0.0.1:8080/GetOpenPositions?user="+user
        r= requests.get(p)
        symbol=""
        share=""
        for i in r.text.splitlines():
            if "Position Symbol" in i:

                symbol = find_between(i, "Symbol=", " ")[1:-1]

                price =  float(find_between(i, "AveragePrice=", " ")[1:-1])
                share = int(find_between(i, "Volume=", " ")[1:-1])

                
                d[symbol] = (price,share) 
        #log_print("Ppro_in:, get positions:",d)
        return d
    except Exception as e:
        #PrintException(e)
        return None
