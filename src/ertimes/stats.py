#Julianne's year_range function
def year_range(data):
    earliest_year = data['year'].min()
    latest_year=data['year'].max()
    return "earliest year: " + str(earliest_year), "latest year: " + str(latest_year)
