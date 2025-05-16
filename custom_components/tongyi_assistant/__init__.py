"""The TongyiAI Conrtrol integration."""
from __future__ import annotations

import json
import re
import random

from functools import partial
import logging
from typing import Any, Literal

from string import Template

import dashscope



from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, TemplateError
from homeassistant.helpers import intent, template, entity_registry,area_registry
from homeassistant.util import ulid

from .const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_CHAT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    ENTITY_TEMPLATE,
    PROMPT_TEMPLATE,
)

_LOGGER = logging.getLogger(__name__)

entity_template = Template(ENTITY_TEMPLATE)
prompt_template = Template(PROMPT_TEMPLATE)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TongyiAI Agent from a config entry."""
    dashscope.api_key = entry.data[CONF_API_KEY]

    #try:
    #    await hass.async_add_executor_job(
    #        partial(dashscope.Generation.call(
    #            dashscope.Generation.Models.qwen_turbo,
    #            messages=messages,
    #            # set the random seed, optional, default to 1234 if not set
    #            seed=1234,
    #            result_format='message',  # set the result to be "message" format.
    #        ), request_timeout=10)
    #    )
    #except error.AuthenticationError as err:
    #    _LOGGER.error("Invalid API key: %s", err)
    #    return False
    #except error.TongyiAIError as err:
    #    raise ConfigEntryNotReady(err) from err

    conversation.async_set_agent(hass, entry, TongyiAIAgent(hass, entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload TongyiAI Agent."""
    #openai.api_key = None
    conversation.async_unset_agent(hass, entry)
    return True



def _entry_ext_dict(entry: er.RegistryEntry) -> dict[str, Any]:
    """Convert entry to API format."""
    data = entry.as_partial_dict
    data["aliases"] = entry.aliases
    data["capabilities"] = entry.capabilities
    data["device_class"] = entry.device_class
    data["original_device_class"] = entry.original_device_class
    data["original_icon"] = entry.original_icon
    return data

class TongyiAIAgent(conversation.AbstractConversationAgent):
    """TongyiAI Conrtrol Agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.history: dict[str, list[dict]] = {}

    @property
    def attribution(self):
        """Return the attribution."""
        return {"name": "Powered by Tongyi", "url": "https://tongyi.aliyun.com/"}

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL
    def find_last_brace(self,s):
        last_brace_index = -1
        for i, char in enumerate(reversed(s)):
            if char == '}':
                last_brace_index = len(s) - 1 - i
                break
        if last_brace_index >= 0:
            last_brace = s[last_brace_index]
            return last_brace_index
        else:
            return -2

    async def async_generate_tongyi_call(self, model, max_tokens, top_p, temperature, sending_messages):
        """调用通义大模型API并处理可能的错误。"""
        try:
            # 将同步方法放入执行器（线程池）中执行
            result = await self.hass.async_add_executor_job(
                lambda: dashscope.Generation.call(
                model=model,
                messages=sending_messages,
                seed=random.randint(1, 10000),
                max_tokens=max_tokens,
                top_p=top_p,
                temperature=temperature,
                result_format='message')
            )
            return result
        except Exception as exc:
            _LOGGER.error("调用通义API时出错: %s", exc)
            return None

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:

        """ Options input """

        # 获取配置选项
        raw_prompt = self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
        model = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        max_tokens = self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        top_p = self.entry.options.get(CONF_TOP_P, DEFAULT_TOP_P)
        temperature = self.entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)

        # 获取暴露的实体
        exposed_entities = self.get_exposed_entities()
        
        # 生成提示词
        try:
            prompt = self._async_generate_prompt(raw_prompt, exposed_entities)
        except TemplateError as err:
            _LOGGER.error("渲染提示词模板时出错: %s", err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"抱歉，提示词模板渲染出错: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=user_input.conversation_id or ulid.ulid()
            )

        # 处理对话历史
        if user_input.conversation_id in self.history:
            conversation_id = user_input.conversation_id
            messages = self.history[conversation_id]
        else:
            conversation_id = ulid.ulid()
            messages = [{"role": "system", "content": prompt}]

        # 添加用户消息
        messages.append({"role": "user", "content": user_input.text})

        _LOGGER.debug("发送到通义的提示词: 模型=%s, 最大令牌=%s, top_p=%s, 温度=%s", 
                     model, max_tokens, top_p, temperature)

        # 创建发送消息列表
        sending_messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input.text}
        ]

        # call Tongyi
        #try:
        #    result = await self.hass.async_add_executor_job(dashscope.Generation.call(dashscope.Generation.Models.qwen_turbo,messages=sending_messages,seed=random.randint(1, 10000),result_format='message'))
       #     result = await openai.ChatCompletion.acreate(
       #         model=model,
       #         messages=sending_messages,
       #         max_tokens=max_tokens,
       #         top_p=top_p,
       #         temperature=temperature,
       #         user=conversation_id,
       #     )
       # except error.TongyiAIError as err:
       #     intent_response = intent.IntentResponse(language=user_input.language)
       #     intent_response.async_set_error(
       #         intent.IntentResponseErrorCode.UNKNOWN,
       #         f"Sorry, I had a problem talking to TongyiAI: {err}",
       #     )
       #     return conversation.ConversationResult(
       #         response=intent_response, conversation_id=conversation_id
       #     )
        result = await self.async_generate_tongyi_call(model, max_tokens, top_p, temperature, sending_messages)
        if not result:
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                "抱歉，调用通义API时出现问题，请稍后再试。",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )
            
        _LOGGER.info("通义响应: %s", result)
        
        try:
            content = result["output"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as err:
            _LOGGER.error("解析通义响应时出错: %s", err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                "抱歉，解析通义响应时出现问题，请稍后再试。",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )

        # 设置默认回复
        reply = content
        json_response = None

        # 尝试解析JSON响应
        try:
            json_response = json.loads(content)
            _LOGGER.debug("成功解析JSON响应: %s", json_response)
        except json.JSONDecodeError:
            # 如果不是有效的JSON，尝试从响应中提取JSON
            start_idx = content.find('{')
            end_idx = self.find_last_brace(content) + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_string = content[start_idx:end_idx]
                try:
                    json_response = json.loads(json_string)
                    _LOGGER.debug("从响应中提取JSON成功: %s", json_response)
                except json.JSONDecodeError:
                    _LOGGER.info('从响应中提取JSON失败: %s', json_string)
            else:
                _LOGGER.info('响应中未找到有效的JSON结构: %s', content)

        # 处理JSON响应中的实体操作
        if json_response is not None:
            try:
                entities = json_response.get("entities", [])
                for entity in entities:
                    if not entity.get("service") or not entity.get("service_data", {}).get("entity_id"):
                        _LOGGER.warning("实体数据不完整: %s", entity)
                        continue
                        
                    entity_id = entity['service_data']['entity_id']
                    if "." not in entity_id:
                        _LOGGER.warning("无效的实体ID: %s", entity_id)
                        continue
                        
                    domain, device = entity_id.split('.', 1)
                    
                    service = entity['service']
                    if "." in service:
                        domain, service = service.split('.', 1)
                    
                    _LOGGER.info("调用服务: %s.%s %s", domain, service, entity['service_data'])
                    await self.hass.services.async_call(domain, service, entity['service_data'])
            except Exception as err:
                _LOGGER.error("处理实体操作时出错: %s", err)

            # 获取助手回复
            reply = json_response.get('assistant', reply)

        messages.append(reply)
        #messages.append(result["choices"][0]["message"])
        self.history[conversation_id] = messages

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(reply)
        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    def _async_generate_prompt(self, raw_prompt: str, exposed_entities) -> str:
        """Generate a prompt for the user."""
        return template.Template(raw_prompt, self.hass).async_render(
            {
                "ha_name": self.hass.config.location_name,
                "exposed_entities": exposed_entities,
            },
            parse_result=False,
        )

    def get_exposed_entities(self):
        states = [
            state
            for state in self.hass.states.async_all()
            if async_should_expose(self.hass, conversation.DOMAIN, state.entity_id)
        ]
        registry = entity_registry.async_get(self.hass)
        exposed_entities = []
        '''
        方法1
        areas = area_registry.async_list_areas()
        for area in areas:
            entities = []
            entities = await self.hass.states.async_select_area(area)
            for entity in entities:
                entities.append(
                {
                    "entity_id": entity.entity_id,
                    "name": entity.friendly_name,
                    "state": self.hass.states.get(entity.entity_id).state,
                    "aliases": entity.aliases,
                }
                )
            exposed_entities.append(
            {
                "area_name":area,
                "entities",entities
            })

        方法2
        areas = self.hass.async_list_areas()
        for area in areas:
            entities = []
            for state in states:
            if 'area_name' in state.context:

                exposed_entities.append((state.entity_id, state.context.area_name))

        方法3
        area_reg = area_registry.async_get(hass)
        return [area.id for area in area_reg.async_list_areas()]

        area_reg.async_list_areas()
        if area := area_reg.async_get_area(area_id)
            area.name
        area_name()

        exposed_entities = []


        '''
        for state in states:
            entity_id = state.entity_id
            entity = registry.entities.get(entity_id)

            aliases = []
            if entity and entity.aliases:
                aliases = entity.aliases

            exposed_entities.append(
                {
                    "entity_id": entity_id,
                    "name": state.name,
                    "state": self.hass.states.get(entity_id).state,
                    "aliases": aliases,
                }
            )
        return exposed_entities
