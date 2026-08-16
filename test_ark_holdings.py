from collect_ark_holdings import parse_csv


def test_parse_csv_keeps_holdings_and_drops_footer():
    raw = b"date,fund,company,ticker,cusip,shares,market value($),weight(%)\n08/17/2026,ARKK,EXAMPLE INC,EXM,123,100,1000,1.2\n,,,,,,,\nThe principal risks,,,,,,,\n"
    as_of, rows = parse_csv(raw, "ARKK")
    assert as_of == "08/17/2026"
    assert len(rows) == 1
    assert rows[0]["company"] == "EXAMPLE INC"
    assert rows[0]["fund_ticker"] == "ARKK"
