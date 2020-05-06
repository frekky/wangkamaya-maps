from featuremap.models import Place
 
def find_matching_place(source, source_id):
    pls = Place.objects.filter(source=source, source_id=source_id)
    if pls.count() > 1:
        #print("Removing duplicates: %s" % pls)
        pls.delete()
    elif pls.count() == 1:
        #print("Updating place '%s'" % pls[0])
        return pls
