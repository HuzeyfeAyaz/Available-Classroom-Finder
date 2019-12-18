from Tkinter import *
from ttk import Combobox, Treeview
import mysearchengine
from bs4 import BeautifulSoup
import urllib2
import operator


class Classroom(object):
    """docstring for Classroom"""

    def __init__(self, building_num, floor_num, room_num):
        self.building_num = building_num   # corresponding building number
        self.floor_num = floor_num      # corresponding floor num
        self.room_num = room_num        # corresponding room number
        self.class_times = {}   # key = day, value = class time interval in that day to compute availability score
        self.traffic_score = {}  # key = day of the week, value = traffic score

    def get_distance_from(self, another_classroom_obj):
        building = abs(int(another_classroom_obj.building_num) - int(self.building_num)) * 100  # building differences
        floor = abs(int(another_classroom_obj.floor_num) - int(self.floor_num)) * 200   # floor num differences
        room = abs(int(another_classroom_obj.room_num[1:]) - int(self.room_num[1:])) * 50   # room num differences
        closeness = building + floor + room     # to sum all values
        if closeness == 0:  # if closeness is 0 thet means that is the same class and;
            closeness = 100     # make it score 100
        return float(closeness)  # return to take each classroom value


class Building(object):
    """docstring for Building"""

    def __init__(self, name):
        self.name = name        # building name like ACAD BUILDING 1
        self.classrooms = []    # a list of corresponding classroom objects sorted by room num


class Day(object):
    """docstring for Day"""

    def __init__(self, name):
        self.name = name    # day of week
        self.time_slots = {}    # key=time slice like 11:00 value=classroom obj which available in that day and hour


class SearchResultItem(object):
    """docstring for SearchResultItem"""

    def __init__(self, classroom):
        self.classroom = classroom  # a classroom obj
        self.availability_score = 0  # availability score of corresponding classroom obj
        self.traffic_score = 0  # traffic score of classroom object
        self.closeness_score = 0    # closeness score of clasroom obj
        self.available_slots = set()  # available slots of that classroom in that day

    def compute_availability_score(self, start_time, end_time, day):
        score = 0    # score keeps the total time interval of classes
        try:
            start_time, end_time = int(start_time[:2]), int(end_time[:2])  # to seperate start time and end time
        except ValueError:  # when start time is 09 it give a ValueError thats why i use the except part
            start_time, end_time = 9, int(end_time[:2])  # then we solve the problem :)
        int_ = end_time - start_time    # int means interval total time between end time and start time
        N = int_ * 60   # to convert interval to minutes
        start_time = start_time * 60    # also convert start time to min
        end_time = end_time * 60  # to convert end time to min
        try:  # try for the KeyError of class_times
            for time in self.classroom.class_times[day]:  # class times to keep class time in that day
                time0 = (int(time[0][:2]) * 60) + (int(time[0][3:]))   # time0 is start time of class
                time1 = (int(time[1][:2]) * 60) + (int(time[1][3:]))   # time1 is end time of class

                if time0 <= start_time and time1 >= end_time:  # if time interval in the class time
                    continue  # don't calculate anything because the default availabilty score is 0
                elif time1 <= start_time or time0 >= end_time:  # if time interval out of the class range
                    self.availability_score = float(100)   # set its availabilty score as a 100
                elif time0 >= start_time and time1 <= end_time:   # if class time in user time interval
                    score = score + (time1 - time0)   # take a range of class time
                elif (time0 >= start_time and time0 < end_time) and time1 > end_time:  # if just class start time in user time interval
                    score = score + (end_time - time0)
                elif (time1 > start_time and time1 <= end_time) and time0 < start_time:  # if just class end time ""
                    score = score + (time1 - start_time)

            if score != 0:  # if score not equal to 0 compute availability score
                A = N - score
                self.availability_score = 100 * (float(A) / N)
        except KeyError:  # if it is give a KeyError that means classroom does not have a lesson in that day
            self.availability_score = float(100)


class Searcher(object):
    """docstring for Searcher"""

    def __init__(self):
        self.days = {}   # key=dayname, value=corresponding day object
        self.buildings = {}     # key=building name, value = corresponding building obj
        self.classroom_objects = {}  # classroom objects to keep each classroom objects in a dict and take the same obj.

    def fetch(self, link_):   # fetch method to fetch data from webside
        contents = urllib2.urlopen(link_).read()  # to open link and read the content
        soup = BeautifulSoup(contents, 'html.parser')  # to parse it using BeautifulSoup
        for tr in soup.find_all('tr'):   # to find all tr tags which keep the part of each class and classroom info.
            spans = tr.find_all('span')   # to find all span tags in tr
            try:
                build_info = spans[4].string.encode('utf8').split()  # spans[4] keep building values and classroom info.
                if 'ACAD' not in build_info or 'KEMAL' in build_info:  # to eliminate everthing except Acad buildings
                    continue
                days = [eval(repr(string.encode('utf8'))) for string in spans[2].stripped_strings]  # to take days
                times = [eval(repr(string.encode('utf8'))) for string in spans[3].stripped_strings]  # to take times
                if 'Saturday' in days:  # if day is Saturday skip it
                    continue
                if len(days) - len(times) == 1:  # somehimes there are two days but 1 time slot
                    times.append(times[0])  # to append one more time slot in times list
                build_name = ' '.join(build_info[:3])  # to take only build name which ex. Acad Build 1
                classroom = Classroom(int(build_info[2]), int(build_info[3][2]), build_info[3][2:])  # classroom obj
                self.buildings.setdefault(build_name, Building(build_name))  # to create building obj
                if build_info[3] not in self.classroom_objects:  # build_info[3] is keep #4302
                    self.classroom_objects[build_info[3]] = classroom   # to add clssroom obj in classroom_object dict
                    self.buildings[build_name].classrooms.append(classroom)  # and add in corressponding building
                classroom = self.classroom_objects[build_info[3]]  # take same classroom obj from classroom_obj class
                for num in range(len(days)):  # the main reason of using same classroom is don't use more memmory
                    self.days.setdefault(days[num], Day(days[num]))  # take one day in days list
                    time_int = times[num].split('-')  # take time slots of that day
                    if int(time_int[0][:2]) >= 19 or int(time_int[1][:2]) > 19:  # if time greather than 19:00
                        if int(time_int[0][:2]) >= 19:  # if start time greather than 19:00
                            continue  # skip it
                        else:
                            time_int.pop(1)
                            time_int.append('19:00')   # change the end time with 19:00
                    for week_day in ["Monday", 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:  # to add all days in days dict
                        self.days.setdefault(week_day, Day(week_day))
                        classroom.traffic_score.setdefault(week_day, 0)  # set classroom's traffic score 0
                        for i in range(9, 20):   # to add time interval from 9 to 19
                            self.days[week_day].time_slots.setdefault('%d:00' % i, [])  # to add time slice in time slots
                            if week_day == days[num]:   # if week_day and class day are equal
                                if int(time_int[0][:2]) <= i and int(time_int[1][:2]) > i:  # and i in between time interval
                                    classroom.class_times.setdefault(days[num], [])  # add class day in class_times class
                                    if time_int not in classroom.class_times[days[num]]:  # if time interval not in
                                        classroom.class_times[days[num]].append(time_int)  # append time interval in it
                                        class_time = float(time_int[1][:2]) - float(time_int[0][:2])  # class time to calculate traffic score
                                        classroom.traffic_score[days[num]] += class_time  # add class hour in traffic score
                                    continue  # and continue don't append classroom in days dict for that hour
                            self.days[week_day].time_slots['%d:00' % i].append(classroom)
            except AttributeError:
                pass

    def compute_availability_scores(self, start_time, end_time, day):
        self.search_items = {}   # to keep class number as a key and SearchResultItem objects as value
        self.normalized_availability = {}  # to keep normalized availability score
        for time, list_ in self.days[day].time_slots.items():
            for class_obj in list_:
                class_num = str(class_obj.building_num) + str(class_obj.room_num)  # class num like 4302
                self.search_items.setdefault(class_num, SearchResultItem(class_obj))  # class num and SearchRes. obj
                self.search_items[class_num].available_slots.add(time)  # add in available_slots

        for class_ in self.search_items:
            self.search_items[class_].compute_availability_score(start_time, end_time, day)  # to compute availability
            self.normalized_availability[class_] = self.search_items[class_].availability_score

        self.normalized_availability = mysearchengine.normalizescores(
            self.normalized_availability, smallIsBetter=False)  # to keep normalized values

    def compute_traffic_scores(self, day):
        dict_ = {}  # to keep class_num and result of traffic score calculation
        self.normalized_traffic = {}    # to keep normalized traffic score
        for name, build in self.buildings.items():
            for class_ in build.classrooms:
                if day not in class_.traffic_score:  # if day not exists in traffic score
                    class_.traffic_score[day] = 0  # set its traffic score as 0
                score = class_.traffic_score[day]  # take class traffic score for corresponding day
                result = float(score) / 10  # traffic calculations
                if result == 0.0:  # if result 0 replace it with 0.1
                    result = 0.1
                class_.traffic_score[day] = result  # set class traffic score
                class_num = str(class_.building_num) + str(class_.room_num)
                dict_[class_num] = result  # and add them in dict_ dictionary to normalize
        self.normalized_traffic = mysearchengine.normalizescores(dict_, smallIsBetter=True)

    def compute_closeness_scores(self, building, room_num):
        current_class = ''  # to keep selected class
        closeness = {}  # to keep closeness scores
        self.normalized_closenes = {}
        for classes in self.buildings[building].classrooms:
            if classes.room_num == room_num:  # if classes room number == selected room number
                current_class = classes  # set current objdect
        for name, build in self.buildings.items():
            for another_class in build.classrooms:  # find closeness score using another classes
                closeness[str(another_class.building_num) + str(another_class.room_num)
                          ] = current_class.get_distance_from(another_class)
        self.normalized_closenes = mysearchengine.normalizescores(closeness, smallIsBetter=True)

    def search(self, day, building, room_num, start_time, end_time):
        self.compute_traffic_scores(day)  # to call all methods
        self.compute_availability_scores(start_time, end_time, day)
        self.compute_closeness_scores(building, room_num)
        for class_name, item in self.search_items.items():  # to set all scores in SearchResultItem objects
            item.availability_score = round(self.normalized_availability[class_name], 4)
            item.traffic_score = round(self.normalized_traffic[class_name], 4)
            item.closeness_score = round(self.normalized_closenes[class_name], 4)
        self.getscoredlist()
        return self.overall_scores  # return overall score to use in gui class

    def getscoredlist(self):  # to calculate overall scoress
        self.overall_scores = {}  # to keep overall scores
        for class_name, item in self.search_items.items():
            weights = [item.availability_score, item.traffic_score, item.closeness_score]  # weights to calculate
            score = weights[0] + weights[1] + weights[2]  # total score
            self.overall_scores[item] = score


class Gui(Frame):
    """ Gui class for Graphical User Interface"""

    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.searcher = Searcher()
        self.initUI()

    def initUI(self):
        self.pack(fill=BOTH, expand=True)
        Grid.columnconfigure(self, 0, weight=1)
        Label(self, text='Classroom Finder', font=('Arial', 20, 'bold'), bg='cyan', fg='white').grid(
            sticky=W + E, columnspan=3)  # classroom finder header
        Label(self, text='Url:').grid(column=0, row=1, pady=10, padx=(50, 0))
        self.urlentry = Entry(self, width=100)  # url entry to get url
        self.urlentry.grid(column=1, row=1, padx=(0, 80))
        self.color_label = Label(self, bg='red', width=10)  # color label to make red,yellow,green
        self.color_label.grid(column=0, row=2, sticky=E, columnspan=2, padx=(120), pady=(0, 40))
        self.fetchbtn = Button(self, text='Fetch', height=2, width=10, command=self.dynamic)  # fetch button
        self.fetchbtn.grid(column=1, row=2, sticky=E, padx=(0, 30), pady=(10, 50))
        Label(self, text='Filters', bg='cyan', fg='white', font=('Arial', 20, 'bold'), width=10).grid(
            column=0, row=3, padx=10)
        self.frame = Frame(self, borderwidth=3, relief=GROOVE)  # frame to keep filters part
        self.frame.grid(column=0, row=4, columnspan=3, sticky=W + E + S + N, pady=10, padx=10)
        Label(self.frame, text='Where am I?').grid(sticky=W)
        self.where_combo = Combobox(self.frame, state='readonly')  # where am i combobox
        self.where_combo.grid(column=1, row=0, pady=20)
        self.where_combo.bind('<<ComboboxSelected>>', self.change_build)  # to update room button wrt where combo
        Label(self.frame, text='Room').grid(sticky=W)
        self.room_combo = Combobox(self.frame, state='readonly')  # rooms combobox
        self.room_combo.grid(column=1, row=1)
        Label(self.frame, text='Start').grid(sticky=W)
        self.start_combo = Combobox(self.frame, state='readonly', width=7)  # start time combobox
        self.start_combo.grid(column=1, row=2, pady=20, sticky=W)
        Label(self.frame, text='End').grid(column=2, row=2, sticky=W)
        self.end_combo = Combobox(self.frame, state='readonly', width=7)  # end time combobox
        self.end_combo.grid(column=3, row=2, sticky=W)
        Label(self.frame, text='Day').grid(sticky=W)
        self.day_combo = Combobox(self.frame, state='readonly')  # days combobox
        self.day_combo.grid(column=1, row=3, pady=(0, 20))
        self.search = Button(self.frame, text='Search', width=10, height=2, command=self.add_treeview)  # seach button
        self.search.grid(padx=(0, 50), columnspan=2)
        Label(self.frame, text='Classroom results', bg='gray', fg='white').grid(
            sticky=N + E + W, column=4, row=0, rowspan=5, padx=(55, 0))
        self.scroll = Scrollbar(self.frame, orient='vertical')   # vertical scrollbar for treeview
        self.tree = Treeview(self.frame, columns=('', '', '', '', ''), selectmode='extended', show='headings')
        listofcolumn = ['Room', 'Traffic', 'Availability %', 'Closeness', 'Overall Score']  # colums to treeview
        counter = 1
        for column in listofcolumn:
            self.tree.column('#' + str(counter), width=90)  # to resize columns
            self.tree.heading('#' + str(counter), text=column, anchor=CENTER)  # to set headings
            counter += 1
        self.scroll.config(command=self.tree.yview)
        self.tree.config(yscrollcommand=self.scroll.set)
        self.tree.grid(column=4, row=0, rowspan=5, padx=(40, 0), pady=(30, 0))
        self.scroll.grid(column=5, row=0, rowspan=5, sticky=N + S, pady=(30, 0))
        self.urlentry.insert(0, 'https://www.sehir.edu.tr/en/announcements/2018-2019-bahar-donemi-ders-programi')

    def dynamic(self):
        self.color_label.configure(bg='yellow')  # make color label yellow at the beginning of the process
        self.update_idletasks()
        self.searcher.fetch(self.urlentry.get())  # to call fetch method in searcher class to start process
        self.color_label.configure(bg='green')
        room_num = [room.room_num for room in self.searcher.buildings['ACAD BUILD 1'].classrooms]
        self.where_combo.configure(values=[build for build in sorted(self.searcher.buildings)])
        self.where_combo.current(0)  # to get values in combobox and set value 0 as a default
        self.room_combo.configure(values=[room for room in sorted(room_num)])
        self.room_combo.current(0)
        self.start_combo.configure(values=["{}:00".format(time) for time in range(9, 20)])
        self.start_combo.current(0)  # start and end combo both have the same interval from 9 to 19
        self.end_combo.configure(values=["{}:00".format(time) for time in range(9, 20)])
        self.end_combo.current(len(self.end_combo['values']) - 1)
        self.day_combo.configure(values=["Monday", 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        self.day_combo.current(0)

    def change_build(self, event):  # when where am i combobox chance, room combobox also chance
        building = self.where_combo.get()
        room_num = [room.room_num for room in self.searcher.buildings[building].classrooms]
        self.room_combo.configure(values=[room for room in sorted(room_num)])
        self.room_combo.current(0)

    def add_treeview(self):  # to add scores in treeview
        self.tree.delete(*self.tree.get_children())
        self.overall_scores = self.searcher.search(
            self.day_combo.get(), self.where_combo.get(), self.room_combo.get(),
            self.start_combo.get(), self.end_combo.get())  # key operator for the sorted dict by values which overall score
        for item, score in sorted(self.overall_scores.items(), key=operator.itemgetter(1), reverse=True):
            if item.availability_score == 0:  # to avoid from availability score 0
                continue
            room = str(item.classroom.building_num) + str(item.classroom.room_num)
            self.tree.insert('', 'end', values=(
                room, item.traffic_score, item.availability_score, item.closeness_score, score))


def main():
    window = Tk()
    window.geometry("850x600")
    window.title("")
    app = Gui(window)
    window.mainloop()


main()
