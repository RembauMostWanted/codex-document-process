from pdf_color_facts.pdfplumber_backend import _rgb, _text_spans


def test_pdf_colour_operands_are_converted_to_rgb():
    assert _rgb(0.5) == (128, 128, 128)
    assert _rgb((0, 90 / 255, 90 / 255)) == (0, 90, 90)
    assert _rgb((1, 0, 0, 0)) == (0, 255, 255)
    assert _rgb(None) is None


def test_adjacent_words_form_a_positioned_text_span():
    words = [
        {"text": "Lower", "x0": 20, "x1": 45, "top": 100, "bottom": 110},
        {"text": "vulnerability", "x0": 48, "x1": 105, "top": 100.5, "bottom": 110.5},
        {"text": "Elsewhere", "x0": 200, "x1": 250, "top": 100, "bottom": 110},
    ]
    spans = _text_spans(words)
    assert [span.text for span in spans] == ["Lower vulnerability", "Elsewhere"]
    assert spans[0].bbox.x0 == 20
    assert spans[0].bbox.x1 == 105
