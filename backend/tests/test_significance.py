from app.intelligence.significance import classify, significance_score


def test_stable_small_move():
    result = significance_score(0.2, 0.02, 20_000_000, 21_000_000)
    assert result["severity"] == "STABLE"
    assert result["score"] < 30


def test_high_abnormal_move():
    result = significance_score(8.0, 0.015, 90_000_000, 40_000_000)
    assert result["score"] >= 80
    assert result["severity"] == "HIGH"


def test_same_percent_means_different_things_for_different_names():
    quiet = significance_score(2.0, 0.010, 1_000_000, 1_000_000)  # 2% on a name that moves 1%/day
    noisy = significance_score(2.0, 0.040, 1_000_000, 1_000_000)  # 2% on a name that moves 4%/day
    assert quiet["score"] > noisy["score"]
    assert quiet["severity"] in {"MEANINGFUL", "HIGH"}
    assert noisy["severity"] == "STABLE"


def test_volume_alone_cannot_escalate_a_flat_price():
    flat = significance_score(0.0, 0.02, 500_000_000, 40_000_000)
    assert flat["score"] == 0
    assert flat["severity"] == "STABLE"


def test_volume_corroborates_a_real_move():
    quiet_volume = significance_score(4.0, 0.02, 40_000_000, 40_000_000)
    heavy_volume = significance_score(4.0, 0.02, 120_000_000, 40_000_000)
    assert heavy_volume["score"] > quiet_volume["score"]


def test_classify_bands():
    assert classify(10) == "STABLE"
    assert classify(40) == "NOTABLE"
    assert classify(70) == "MEANINGFUL"
    assert classify(90) == "HIGH"


def test_sensitivity_changes_outlier_band():
    args = (3.2, 0.018, 50_000_000, 40_000_000)
    quiet = significance_score(*args, sensitivity="conservative")
    move = significance_score(*args, sensitivity="balanced")
    loud = significance_score(*args, sensitivity="sensitive")
    assert quiet["score"] < move["score"] < loud["score"]
    assert classify(72, "balanced") == "MEANINGFUL"
    assert classify(72, "sensitive") == "HIGH"
    assert classify(72, "conservative") == "MEANINGFUL"
