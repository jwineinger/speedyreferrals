import re, sys
from django.template.defaultfilters import slugify
from referrals.base.models import Specialty, Group, Specialist

def parse_group(line):
  try:
    group_name = re.match(r'^[^-\(]+', line[1:]).group()
  except AttributeError:
    pass

  try:
    location = re.search(r'-([^\-(]+)', line).group(1)
  except AttributeError:
    location = ''

  try:
    docs = re.search(r'\((.+)\)', line).group(1)
    doctors = []
    for name in docs.split(';'):
      last,first = name.split(',')
      doctors.append((last.strip(), first.strip()))
  except AttributeError:
    doctors = []

  try:
    numbers = re.findall(r"\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})", line)
  except AttributeError:
    pass

  return {'name' : group_name.strip(), 'location': location.strip(), 'doctors':doctors, 'numbers' : numbers}



mode = 0 # look for new speciality
for line in open(sys.argv[1], 'rb'):
  line = line.rstrip()

  if mode == 0:
    try:
      specialty_name = re.match(r'^[a-zA-Z\s].+', line).group()
      new_specialty = Specialty()
      new_specialty.name = specialty_name.strip()
      new_specialty.slug = slugify(specialty_name)
      new_specialty.save()
      print "Created %s" % new_specialty
      mode = 1  # look for notes or groups for a specialty
    except AttributeError:
      pass

  elif mode == 1:
    try:
      specialty_note = re.match(r'^\s+.+', line).group()
      new_specialty.note = specialty_note.strip()
      new_specialty.save()
      print "  Added Note: %s " % specialty_note
    except AttributeError:
      pass

    try:
      group = re.match(r'\*.+', line).group()
      group_info = parse_group(line)
      new_group = Group()
      new_group.specialty_id = new_specialty.id
      new_group.name = group_info['name']
      new_group.location = group_info['location']
      new_group.preferred = 0
      try:
        new_group.phone = '-'.join(group_info['numbers'][0])
      except IndexError:
        new_group.phone = ''
      try:
        new_group.fax = '-'.join(group_info['numbers'][1])
      except IndexError:
        new_group.fax = ''
      try:
        new_group.medical_records_fax = '-'.join(group_info['numbers'][2])
      except IndexError:
        new_group.medical_records_fax = ''
      new_group.save()

      for last,first in group_info['doctors']:
          new_specialist = Specialist()
          new_specialist.group_id = new_group.id
          new_specialist.first_name = first
          new_specialist.last_name = last
          new_specialist.preferred = 0
          new_specialist.save()

      mode = 2
    except AttributeError:
      pass

    try:
      dummy = re.match(r'^$', line).group()
      mode = 0
      new_specialty = None
      new_group = None
      new_specialist = None
    except AttributeError:
      pass


  elif mode == 2:
    try:
      group_note = re.match(r'^\s+.+', line).group()
      new_group.note += "\n"+group_note.strip()
      new_group.save()
    except AttributeError:
      pass

    try:
      group = re.match(r'\*.+', line).group()
      group_info = parse_group(line)
      new_group = Group()
      new_group.specialty_id = new_specialty.id
      new_group.name = group_info['name']
      new_group.location = group_info['location']
      new_group.preferred = 0
      try:
        new_group.phone = '-'.join(group_info['numbers'][0])
      except IndexError:
        new_group.phone = ''
      try:
        new_group.fax = '-'.join(group_info['numbers'][1])
      except IndexError:
        new_group.fax = ''
      try:
        new_group.medical_records_fax = '-'.join(group_info['numbers'][2])
      except IndexError:
        new_group.medical_records_fax = ''
      new_group.save()

      for last,first in group_info['doctors']:
          new_specialist = Specialist()
          new_specialist.group_id = new_group.id
          new_specialist.first_name = first
          new_specialist.last_name = last
          new_specialist.preferred = 0
          new_specialist.save()

    except AttributeError:
      pass

    try:
      dummy = re.match(r'^$', line).group()
      new_specialty = None
      new_group = None
      new_specialist = None
      mode = 0
    except AttributeError:
      pass
