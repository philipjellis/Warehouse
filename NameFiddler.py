def nameFiddle(name, sex, ER='xxx'):
    def findList(lis, strin):
        try:
            ix = lis.index(strin)
            result = True
        except:
            result = False
        return result

    def concat(words):
        words = list(words) # makes a copy
        for i in range(len(words)-1):
            if words[i] in ['Mc','St.','De','De La', 'Jo']:
                words[i+1] = words[i]+' '+words[i+1]
                words[i]=''
        while 1==1:
            try:
                words.pop(words.index(''))
            except:
                break
        return words

    def fid(wd,st):
        (pt1,ch,pt2) = wd.partition(st)
        return pt1+ch+pt2.capitalize()

    def dotw(wd):
        if wd in ['.',',']:
            return ''
        else:
            wds = wd.split('.')
            for w in wds:
                if len(w) == 1:
                    w = w.upper()+'.'
            return ''.join(wds)

    def fiddle(wd):
        wd = fid(wd,'-')
        wd = fid(wd,'=')
        wd = fid(wd,'Mc')
        wd = fid(wd,"O'")
        wd = fid(wd,"D'")
        if wd == 'St': wd = 'St.'
        return wd

    def procSuff(name):
        name = name
        suff = ''
        suffStrings = ['Iii','Iv ','Iv,','Ii','Jr.','Jr','Sr.','Sr,',' Md']
        for suf in suffStrings:
            ix = name.find(suf)
            if ix > -1:
                if suf not in ['Iv','Ii','Iii',' Md']:
                    suff = suf.strip('.,').capitalize()+'.'
                else:
                    suff = suf.upper()
                name = name.replace(suf.strip('.,'),'')
        return (name, suff)

    def procTitle(name, sex):
        name = name
        title = ''
        titStrings = ['SR. ','Sr. ','SR ','Sr ','Sister ','SISTER ']
        if sex  == 'F':
            title = 'Ms.'
        elif sex == 'M':
            title = 'Mr.'
        for tit in titStrings:
            ix = name.find(tit)
            if ix > -1:
                if tit.upper().strip('.') == 'SR':
                    title = 'Sr.'
                else:
                    title = tit
                name = name.replace(tit.strip(),'')
        return (name, title)
                
    def parenth(a):
            (pt1,br,pt2) = a.partition('(')
            (pt2,br,pt3) = pt2.partition(')')
            if len(pt2) > 0: pt2 = '('+pt2+')'
            return (pt1+pt3,pt2)

    def mainFiddle(words):
        words = [fiddle(word) for word in words]
        words = concat(words)
        return words    

    fname, lname, suffix, title, middle, namecomments  = '','','','','',''
    temp = name.title()
    (temp,title) = procTitle(temp,sex)
    (temp,suffix) = procSuff(temp)        
    words = temp.split()
    words = [dotw(w) for w in words] # puts a period afer all single initials
    temp = ' '.join(words)
    (temp,namecomments) = parenth(temp)
    if temp.count(',') == 0:
        temp +=', '
    (lname,temp) = temp.split(',',1)
    lname = lname.split()
    temp = temp.split()

    lname = mainFiddle(lname)
    temp = mainFiddle(temp)
    namecomments = fiddle(namecomments)
    
    if len(temp) > 0:
        fname = temp.pop(0).strip(', ')
    middle = ' '.join(temp)

    lname = ' '.join(lname)
    if len(fname.strip('.')) < 2 and len(middle.strip('.')) > 1:
        (fname, middle) = (middle, fname)
    if len(middle) == 1: middle +='.'
    if (lname == 'M.') and (ER == 'MFH'): #nun from Mother Francis
        lname = ''
        fname = 'M.'+fname
    if middle == '..': middle = ''
    return (fname, lname, middle, title, suffix, namecomments)
