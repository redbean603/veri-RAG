links = [
    # Company → Industry
    {"source": "c_samsung", "target": "ind_semiconductor", "rel": "BELONGS_TO"},
    {"source": "c_sk", "target": "ind_semiconductor", "rel": "BELONGS_TO"},
    {"source": "c_hyundai", "target": "ind_auto", "rel": "BELONGS_TO"},
    {"source": "c_kia", "target": "ind_auto", "rel": "BELONGS_TO"},
    {"source": "c_lge", "target": "ind_battery", "rel": "BELONGS_TO"},
    {"source": "c_posco", "target": "ind_steel", "rel": "BELONGS_TO"},
    {"source": "c_kakao", "target": "ind_it", "rel": "BELONGS_TO"},
    {"source": "c_naver", "target": "ind_it", "rel": "BELONGS_TO"},
    {"source": "c_celltrion", "target": "ind_bio", "rel": "BELONGS_TO"},
    {"source": "c_hanwha", "target": "ind_semiconductor", "rel": "BELONGS_TO"},
    {"source": "c_kb", "target": "ind_finance", "rel": "BELONGS_TO"},
    {"source": "c_shinhan", "target": "ind_finance", "rel": "BELONGS_TO"},
    {"source": "c_kakaobank", "target": "ind_finance", "rel": "BELONGS_TO"},
    {"source": "c_toss", "target": "ind_finance", "rel": "BELONGS_TO"},
    {"source": "c_krafton", "target": "ind_it", "rel": "BELONGS_TO"},
    {"source": "c_hhi", "target": "ind_shipbuilding", "rel": "BELONGS_TO"},

    # Person → Company / Org
    {"source": "p_lee_jw", "target": "c_samsung", "rel": "LEADS"},
    {"source": "p_choi_tw", "target": "c_sk", "rel": "LEADS"},
    {"source": "p_chung_ej", "target": "c_hyundai", "rel": "LEADS"},
    {"source": "p_lee_hz", "target": "c_naver", "rel": "LEADS"},
    {"source": "p_rhee", "target": "o_bok", "rel": "LEADS"},
    {"source": "p_choi_sg", "target": "o_moef", "rel": "LEADS"},
    {"source": "p_kim_bs", "target": "o_fsc", "rel": "LEADS"},

    # Org → Org 관계성
    {"source": "o_bok", "target": "o_moef", "rel": "COLLABORATES_WITH"},
    {"source": "o_fsc", "target": "o_fss", "rel": "SUPERVISES"},
    {"source": "o_ftc", "target": "o_fsc", "rel": "COLLABORATES_WITH"},
    {"source": "o_fed", "target": "o_bok", "rel": "AFFECTS"},
    {"source": "o_imf", "target": "o_bok", "rel": "COLLABORATES_WITH"},
    {"source": "o_krx", "target": "o_fsc", "rel": "SUPERVISED_BY"},



    # Event 연결망
    {"source": "ev_fomc", "target": "o_fed", "rel": "HELD_BY"},
    {"source": "ev_fomc", "target": "a_usdkrw", "rel": "AFFECTS"},
    {"source": "ev_fomc", "target": "a_kospi", "rel": "AFFECTS"},
    {"source": "ev_mpc", "target": "o_bok", "rel": "HELD_BY"},
    {"source": "ev_mpc", "target": "pol_rate", "rel": "DECIDES"},
    {"source": "ev_legoland", "target": "ind_finance", "rel": "AFFECTS"},
    {"source": "ev_taeyoung", "target": "pol_pf", "rel": "TRIGGERS"},
    {"source": "ev_samsung_q", "target": "c_samsung", "rel": "ANNOUNCED_BY"},
    {"source": "ev_chips_war", "target": "c_samsung", "rel": "AFFECTS"},
    {"source": "ev_chips_war", "target": "c_sk", "rel": "AFFECTS"},

    # Asset 지표 관계
    {"source": "a_dram", "target": "c_samsung", "rel": "MEASURES"},
    {"source": "a_dram", "target": "c_sk", "rel": "MEASURES"},
    {"source": "a_lithium", "target": "c_lge", "rel": "AFFECTS"},
    {"source": "a_oil", "target": "ind_energy", "rel": "AFFECTS"},
    {"source": "a_kospi", "target": "o_krx", "rel": "TRADED_AT"},
    {"source": "a_housepr", "target": "pol_dsr", "rel": "AFFECTED_BY"},

    # # News → Source
    # {"source": "n1", "target": "src_hankyung", "rel": "SOURCE_FROM"},
    # {"source": "n2", "target": "src_yonhap", "rel": "SOURCE_FROM"},
    # {"source": "n3", "target": "src_reuters", "rel": "SOURCE_FROM"},
    # {"source": "n4", "target": "src_maeil", "rel": "SOURCE_FROM"},

    # # News → Entity/Claim
    # {"source": "n1", "target": "c_samsung", "rel": "MENTIONS"},
    # {"source": "n2", "target": "pol_rate", "rel": "MENTIONS"},
    # {"source": "n3", "target": "a_usdkrw", "rel": "MENTIONS"},
    # {"source": "n4", "target": "ev_taeyoung", "rel": "MENTIONS"},
    # {"source": "n1", "target": "cl1", "rel": "CONTAINS"},
    # {"source": "n2", "target": "cl2", "rel": "CONTAINS"},
    # {"source": "n3", "target": "cl3", "rel": "CONTAINS"},

    # # Claims 가짜뉴스 핵심 관계 및 모순(Conflicts) 정의
    # {"source": "cl1", "target": "c_samsung", "rel": "ABOUT"},
    # {"source": "cl2", "target": "pol_rate", "rel": "ABOUT"},
    # {"source": "cl3", "target": "a_usdkrw", "rel": "ABOUT"},
    # {"source": "cl1", "target": "src_dart", "rel": "VERIFIED_BY"},
    # {"source": "cl2", "target": "src_ecos", "rel": "VERIFIED_BY"},
    # {"source": "cl1", "target": "cl3", "rel": "SUPPORTS"},
    # {"source": "cl1", "target": "ind_semiconductor", "rel": "CONTRADICTS"}, # ⚠️ 핵심 모순 관계성

    # Multimodal Image 매핑
    {"source": "img1", "target": "n3", "rel": "ILLUSTRATES"},
    {"source": "img2", "target": "c_samsung", "rel": "ABOUT"},
    {"source": "img3", "target": "a_kospi", "rel": "ABOUT"},
    {"source": "src_ecos", "target": "o_bok", "rel": "PUBLISHED_BY"},
    {"source": "src_dart", "target": "o_fss", "rel": "MANAGED_BY"}
]
