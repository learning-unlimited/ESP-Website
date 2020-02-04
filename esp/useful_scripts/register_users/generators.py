import os
import csv
import random
import datetime
import collections


base_dir = os.path.dirname(__file__)

RandomPerson = collections.namedtuple('RandomPerson', (
        'first', 'last', 'middle', 'full', 'comma_full', 'email', 'username',
        'user_type', 'grade', 'dob',
        ))

__all__ = ('random_people',
           'random_address',
           'random_phone',
           'random_classes',
)

def random_userType():
    if random.random() < 0.1:
        return 'Teacher'
    else:
        return 'Student'

def random_people(userType=random_userType):
    " Generate random names. "
    random_name_db = csv.reader(open(os.path.join(base_dir, 'random_names.csv')))
    random_name_db.next()
    random_names = list(random_name_db)
    random.shuffle(random_names)
    for row in random_names:
        row = list(row)
        row.append(random_email(row[0], row[1]))
        row.append(row[0][0].lower() + row[1].lower())
        user_type = userType
        if callable(userType):
            user_type = userType()
        row.append(user_type)
        row.append(random.randint(6, 12))
        row.append(get_random_dob(row[-1]))
        yield RandomPerson(*row)

streets = 'Second Third First Fourth Park Fifth Main Sixth Oak Seventh Pine Maple Cedar Eighth Elm View Washington Ninth Lake Hill'.split()
suffixes = 'St Ave Blvd Cr'.split()

town_names = 'Franklin Clinton Springfield Greenville Salem Fairview Madison Washington Georgetown Arlington Ashland Burlington Manchester Marion Oxford Clayton Jackson Milton Auburn Dayton Lexington Milford Riverside Cleveland Dover Hudson Kingston Newport Oakland Centerville Winchester'.split()

state_names = 'CT MA NY RI ME NJ CA FL'.split()

RandomAddress = collections.namedtuple('RandomAddress', (
        'street', 'city', 'state', 'zip'))

def random_address():
    " Generate random address. "
    while True:
        street = random.choice(streets) + ' ' + random.choice(suffixes)
        street = str(random.randint(1, 2000)) + ' ' + street
        city = random.choice(town_names)
        state = random.choice(state_names)
        zip = '%05d' % (random.randint(1000, 99999))
        yield RandomAddress(street, city, state, zip)


def random_phone():
    while True:
        yield '%03d-%03d-%04d' % (random.randint(100, 700),
                                  random.randint(100, 999),
                                  random.randint(1111, 9999))

email_domains = 'axiak.net'.split()

def random_email(first, last):
    return '%s%s@%s' % (first.lower()[0],
                        last.lower(),
                        random.choice(email_domains))




RandomClass = collections.namedtuple('RandomClass',
                                     ('title',
                                      'description',
                                      'min_grade',
                                      'max_grade',))

def random_classes():
    while True:
        title = ' '.join(random_words(random.randint(2, 5))).title()
        description = course_text[:random.randint(300, 1000)].strip()
        min_grade = random.randint(7, 11)
        max_grade = random.randint(min_grade, 12)
        yield RandomClass(title, description, min_grade, max_grade)

words = [word for word in open('/usr/share/dict/words').read().split()
         if len(word) > 1 and "'" not in word and not word[0].isupper()]


def get_random_dob(grade):
    current_year = int(datetime.datetime.now().year)
    return datetime.date(current_year - grade - 6, 1, 1) + datetime.timedelta(days=random.randint(-182, 182))


def random_words(num_words):
    random.shuffle(words)
    return words[:num_words]

course_text = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam at mi erat, et porta ipsum. Donec consectetur massa vitae mi porttitor condimentum. Quisque eleifend semper tortor ac tincidunt. Donec nec metus urna, non tincidunt magna. Pellentesque nisi purus, euismod nec varius sed, molestie nec turpis. Vestibulum id lectus quam, sit amet accumsan purus. Nam a enim sem. Nam pharetra tellus varius magna egestas euismod. Fusce lacus nisl, feugiat sed auctor nec, pharetra et urna. Nulla malesuada, est et placerat varius, enim nisl condimentum nisl, eget bibendum eros urna ac dui.

Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Ut lobortis pharetra nulla, et porta risus accumsan nec. Curabitur eget risus nec justo dignissim venenatis. Suspendisse arcu est, euismod quis pretium vel, aliquet non lectus. Vivamus ornare varius massa, sit amet lobortis lorem malesuada ac. Suspendisse potenti. Integer neque lorem, accumsan a porttitor eget, suscipit vel purus. Cras dignissim ultricies nulla id convallis. In sit amet magna ut magna posuere dapibus. Donec a felis ante. Phasellus egestas fermentum sapien sit amet semper. Cras fringilla mi vitae augue pharetra ullamcorper id nec mauris. Fusce et risus sem, at imperdiet mi. Ut varius vehicula tellus, in bibendum ligula tristique sed.

Mauris rutrum, libero ut fermentum tincidunt, orci libero commodo lacus, et rhoncus arcu sem at dolor. Mauris vel erat sapien. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Donec vel viverra mi. Nulla quam magna, imperdiet id tincidunt in, rutrum facilisis arcu. Nulla lacinia, velit mollis placerat vulputate, diam neque dapibus mauris, id faucibus velit purus et lacus. Vestibulum dictum, nisi blandit eleifend porttitor, urna neque euismod mi, non facilisis orci turpis sed tortor. Phasellus vel consequat arcu. Fusce semper viverra congue. Donec vitae commodo ligula. Integer eu mi vel diam ullamcorper dapibus nec nec tellus."""
