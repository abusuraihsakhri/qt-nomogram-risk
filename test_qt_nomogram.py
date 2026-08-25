import qt_nomogram as m
def test_smoke():
    r=m.assess_row({'value':10})
    assert isinstance(r, dict)
