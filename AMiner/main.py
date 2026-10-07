import api.paper


PAPER_KEYWORDS = [
    "生命科学",
    "材料化学",
    "高能物理",
    "量子科技",
    "集成电路",
    "新型电力系统",
    "航空航天",
]

DEFAULT_PAGE = 0
DEFAULT_SIZE = 10
DEFAULT_MAX_PAGES = 1


def query_paper_lists(
    size: int = DEFAULT_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> dict[str, list[object]]:
    """按单个关键词分别查询论文列表，每个关键词从第 0 页开始。"""
    results = {}

    for keyword in PAPER_KEYWORDS:
        page = DEFAULT_PAGE
        keyword_results = []

        for _ in range(max_pages):
            keyword_results.append(
                api.paper.get_paper_list(
                    keywords=[keyword],
                    page=page,
                    size=size,
                )
            )
            page += 1

        results[keyword] = keyword_results

    return results


def main():
    """主函数。"""
    return query_paper_lists()


if __name__ == "__main__":
    main()
