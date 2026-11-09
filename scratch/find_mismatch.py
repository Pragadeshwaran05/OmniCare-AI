path = 'templates/doctor/patient_access.html'
with open(path, encoding='utf-8') as f:
    text = f.read().replace('\r\n', '\n')

sub1 = '<!-- STAGE 2: ENTER OTP -->'
sub2 = 'currentChallengeId = data.challenge_id;'

print('sub1 in text:', sub1 in text)
print('sub2 in text:', sub2 in text)

idx1 = text.find(sub1)
print(repr(text[idx1:idx1+150]))

idx2 = text.find(sub2)
print(repr(text[idx2-50:idx2+250]))
