from app.intelligence.significance import classify, significance_score


def test_stable_small_move():
    result = significance_score(0.2, 0.02, 20_000_000, 21_000_000)
    assert result["severity"] == "STABLE"
    assert result["score"] < 30


def test_high_abnormal_move():
    result = significance_score(8.0, 0.015, 90_000_000, 40_000_000)
    assert result["score"] >= 60
    assert result["severity"] in {"MEANINGFUL", "HIGH"}


def test_classify_bands():
    assert classify(10) == "STABLE"
    assert classify(40) == "NOTABLE"
    assert classify(70) == "MEANINGFUL"
    assert classify(90) == "HIGH"
