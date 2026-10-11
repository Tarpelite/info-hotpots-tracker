import os
from openai import OpenAI


def deepseek_api(person_name: str, organization: str) -> str:
    """
    查询某人在某机构中所属的团队名称。

    :param person_name: 人名
    :param organization: 机构名称
    :return: 推断出的团队名称；无法确定时返回 "未知"
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("请先设置 DEEPSEEK_API_KEY 环境变量")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个信息提取与归属判断助手。"
                    "用户会提供一个人名和一个机构名，你需要返回该人在该机构中所属的团队名称。"
                    "团队包括：课题组、实验室、项目组、部门、事业部、研究组等，优先返回最直接、最小颗粒度的团队。"
                    "如果只能确定上级部门，则返回上级部门名称。"
                    "如果存在多个可能团队，用中文顿号分隔。"
                    "如果无法确定，或该人不在该机构，返回“未知”。"
                    "只输出团队名称本身，不要输出解释、推理过程、前缀、引号或多余标点。"
                    "不要编造不存在的团队。"
                ),
            },
            {
                "role": "user",
                "content": f"人名：{person_name}\n机构：{organization}",
            },
        ],
        stream=False,
        # reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    team_name = response.choices[0].message.content
    return team_name.strip() if team_name else "未知"
