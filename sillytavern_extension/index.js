/**
 * Immersive Story Memory Engine - SillyTavern Extension
 * 
 * 功能：
 * 1. 在用户发送消息前获取状态并注入到system prompt
 * 2. 在模型生成assistant_draft后调用后端处理
 * 3. 根据后端响应处理REWRITE和ASK_USER情况
 * 4. 显示状态摘要和最近事件的侧栏面板
 */

// ==================== 配置 ====================
const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8000';
let backendUrl = DEFAULT_BACKEND_URL;
let storyId = null; // 从当前聊天获取

// ==================== 状态摘要函数 ====================
/**
 * 生成状态摘要（10-20行内）
 * @param {Object} state - CanonicalState对象
 * @returns {string} 状态摘要文本
 */
function state_summary(state) {
    if (!state) {
        return "状态未初始化";
    }

    const lines = [];
    lines.push("=== 故事状态摘要 ===");
    
    // 时间信息
    if (state.time) {
        lines.push(`时间: ${state.time.calendar || '未知'}`);
    }
    
    // 地点信息
    if (state.player && state.player.location_id && state.entities && state.entities.locations) {
        const location = state.entities.locations[state.player.location_id];
        lines.push(`地点: ${location ? location.name : state.player.location_id}`);
    }
    
    // 队伍成员
    if (state.player && state.player.party && state.player.party.length > 0) {
        const partyNames = state.player.party
            .map(id => {
                const char = state.entities?.characters?.[id];
                return char ? char.name : id;
            })
            .join(', ');
        lines.push(`队伍: ${partyNames}`);
    } else {
        lines.push("队伍: 无");
    }
    
    // 关键物品（玩家库存中的唯一物品）
    if (state.player && state.player.inventory && state.player.inventory.length > 0) {
        const items = state.player.inventory
            .map(id => {
                const item = state.entities?.items?.[id];
                return item ? item.name : id;
            })
            .join(', ');
        lines.push(`物品: ${items || '无'}`);
    } else {
        lines.push("物品: 无");
    }
    
    // 生命状态（队伍成员的存活状态）
    if (state.player && state.player.party && state.player.party.length > 0) {
        const lifeStatuses = state.player.party
            .map(id => {
                const char = state.entities?.characters?.[id];
                if (!char) return null;
                return `${char.name}: ${char.alive ? '存活' : '已死亡'}`;
            })
            .filter(Boolean)
            .join(', ');
        if (lifeStatuses) {
            lines.push(`生命状态: ${lifeStatuses}`);
        }
    }
    
    // 任务阶段
    if (state.quest) {
        const activeQuests = state.quest.active || [];
        const completedQuests = state.quest.completed || [];
        if (activeQuests.length > 0) {
            const questTitles = activeQuests.map(q => q.title).join(', ');
            lines.push(`进行中任务: ${questTitles}`);
        }
        if (completedQuests.length > 0) {
            lines.push(`已完成任务: ${completedQuests.length}个`);
        }
        if (activeQuests.length === 0 && completedQuests.length === 0) {
            lines.push("任务: 无");
        }
    }
    
    // 轮次信息
    if (state.meta) {
        lines.push(`轮次: ${state.meta.turn || 0}`);
    }
    
    lines.push("===================");
    
    return lines.join('\n');
}

// ==================== API调用函数 ====================
/**
 * 获取当前状态
 * @param {string} storyId - 故事ID
 * @returns {Promise<Object>} CanonicalState
 */
async function fetchState(storyId) {
    try {
        const response = await fetch(`${backendUrl}/state/${storyId}`);
        if (!response.ok) {
            throw new Error(`获取状态失败: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('[Memory Engine] 获取状态失败:', error);
        return null;
    }
}

/**
 * 处理草稿
 * @param {string} storyId - 故事ID
 * @param {string} userMessage - 用户消息
 * @param {string} assistantDraft - 助手草稿
 * @returns {Promise<Object>} DraftProcessResponse
 */
async function processDraft(storyId, userMessage, assistantDraft) {
    try {
        const response = await fetch(`${backendUrl}/draft/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                story_id: storyId,
                user_message: userMessage,
                assistant_draft: assistantDraft,
            }),
        });
        
        if (!response.ok) {
            throw new Error(`处理草稿失败: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('[Memory Engine] 处理草稿失败:', error);
        return null;
    }
}

// ==================== 状态注入 ====================
/**
 * 将状态摘要注入到system prompt
 * @param {string} summary - 状态摘要
 */
function injectStatePanel(summary) {
    // 使用SillyTavern的scriptAPI来修改system prompt
    if (typeof scriptAPI !== 'undefined') {
        // 获取当前system prompt
        const currentSystemPrompt = scriptAPI.getSystemPrompt?.() || '';
        
        // 移除旧的STATE PANEL（如果存在）
        const cleanedPrompt = currentSystemPrompt.replace(
            /=== 故事状态摘要 ===[\s\S]*?===================\n?/g,
            ''
        );
        
        // 在system prompt前追加STATE PANEL
        const newSystemPrompt = `${summary}\n\n${cleanedPrompt}`;
        
        // 设置新的system prompt
        if (scriptAPI.setSystemPrompt) {
            scriptAPI.setSystemPrompt(newSystemPrompt);
        } else if (scriptAPI.modifyContext) {
            scriptAPI.modifyContext({
                system: newSystemPrompt
            });
        }
        
        console.log('[Memory Engine] 状态摘要已注入到system prompt');
    } else {
        // 备用方法：通过扩展设置存储
        if (typeof extension_settings !== 'undefined') {
            if (!extension_settings.memory_engine) {
                extension_settings.memory_engine = {};
            }
            extension_settings.memory_engine.state_summary = summary;
        }
        console.log('[Memory Engine] 状态摘要已生成（备用方法）:', summary);
    }
}

// ==================== 侧栏面板 ====================
let sidebarPanel = null;
let stateSummaryElement = null;
let recentEventsElement = null;

/**
 * 创建侧栏面板
 */
function createSidebarPanel() {
    if (sidebarPanel) {
        return; // 已存在
    }
    
    // 查找SillyTavern的侧栏容器
    const sidebarContainer = document.querySelector('#right-sidebar') || 
                            document.querySelector('.right-sidebar') ||
                            document.querySelector('#sidebar') ||
                            document.body;
    
    sidebarPanel = document.createElement('div');
    sidebarPanel.id = 'memory-engine-panel';
    sidebarPanel.className = 'memory-engine-panel';
    sidebarPanel.innerHTML = `
        <div class="memory-engine-header">
            <h3>故事状态</h3>
            <button id="memory-engine-toggle" class="memory-engine-toggle">折叠</button>
        </div>
        <div id="memory-engine-content" class="memory-engine-content">
            <div class="memory-engine-section">
                <h4>状态摘要</h4>
                <pre id="memory-engine-state-summary" class="memory-engine-summary">加载中...</pre>
            </div>
            <div class="memory-engine-section">
                <h4>最近事件</h4>
                <ul id="memory-engine-recent-events" class="memory-engine-events"></ul>
            </div>
        </div>
    `;
    
    sidebarContainer.appendChild(sidebarPanel);
    
    stateSummaryElement = document.getElementById('memory-engine-state-summary');
    recentEventsElement = document.getElementById('memory-engine-recent-events');
    
    // 折叠/展开功能
    const toggleButton = document.getElementById('memory-engine-toggle');
    const content = document.getElementById('memory-engine-content');
    let isCollapsed = false;
    
    toggleButton.addEventListener('click', () => {
        isCollapsed = !isCollapsed;
        content.style.display = isCollapsed ? 'none' : 'block';
        toggleButton.textContent = isCollapsed ? '展开' : '折叠';
    });
}

/**
 * 更新侧栏面板
 * @param {Object} state - CanonicalState
 * @param {Array} recentEvents - 最近事件列表
 */
function updateSidebarPanel(state, recentEvents) {
    if (!sidebarPanel) {
        createSidebarPanel();
    }
    
    // 更新状态摘要
    if (stateSummaryElement && state) {
        stateSummaryElement.textContent = state_summary(state);
    }
    
    // 更新最近事件
    if (recentEventsElement && recentEvents) {
        recentEventsElement.innerHTML = '';
        if (recentEvents.length === 0) {
            recentEventsElement.innerHTML = '<li>暂无事件</li>';
        } else {
            recentEvents.forEach(event => {
                const li = document.createElement('li');
                li.className = 'memory-engine-event-item';
                li.innerHTML = `
                    <div class="event-summary">${event.summary || '无摘要'}</div>
                    <div class="event-meta">
                        <span class="event-type">${event.type || 'OTHER'}</span>
                        <span class="event-turn">轮次 ${event.turn || 0}</span>
                    </div>
                `;
                recentEventsElement.appendChild(li);
            });
        }
    }
}

// ==================== 扩展初始化 ====================
/**
 * 扩展加载时调用
 */
function onExtensionLoad() {
    console.log('[Memory Engine] 扩展已加载');
    
    // 从扩展设置中读取配置
    if (typeof extension_settings !== 'undefined') {
        if (!extension_settings.memory_engine) {
            extension_settings.memory_engine = {};
        }
        
        backendUrl = extension_settings.memory_engine.backend_url || DEFAULT_BACKEND_URL;
        storyId = extension_settings.memory_engine.story_id || null;
    }
    
    // 等待DOM加载完成后创建侧栏面板
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(createSidebarPanel, 1000); // 延迟创建以确保SillyTavern UI已加载
        });
    } else {
        setTimeout(createSidebarPanel, 1000);
    }
    
    // 创建设置UI
    createSettingsUI();
    
    // 注册SillyTavern事件监听器
    // 方法1: 使用eventSource（如果可用）
    if (typeof eventSource !== 'undefined') {
        eventSource.on('beforeUserMessage', onUserMessageSend);
        eventSource.on('afterAssistantDraft', onAssistantDraftGenerated);
        console.log('[Memory Engine] 已注册事件监听器 (eventSource)');
    }
    
    // 方法2: 使用scriptAPI（如果可用）
    if (typeof scriptAPI !== 'undefined') {
        if (scriptAPI.registerHook) {
            scriptAPI.registerHook('beforeUserMessage', onUserMessageSend);
            scriptAPI.registerHook('afterAssistantDraft', onAssistantDraftGenerated);
            console.log('[Memory Engine] 已注册事件监听器 (scriptAPI)');
        }
    }
    
    // 方法3: 使用DOM事件（备用方法）
    // 监听SillyTavern的消息发送事件
    document.addEventListener('click', (e) => {
        // 检测发送按钮点击
        if (e.target && (e.target.id === 'send_textarea_button' || e.target.closest('#send_textarea_button'))) {
            setTimeout(() => {
                const textarea = document.querySelector('#send_textarea');
                if (textarea && textarea.value.trim()) {
                    onUserMessageSend({ message: textarea.value });
                }
            }, 100);
        }
    });
}

/**
 * 扩展卸载时调用
 */
function onExtensionUnload() {
    console.log('[Memory Engine] 扩展已卸载');
    
    if (sidebarPanel) {
        sidebarPanel.remove();
        sidebarPanel = null;
    }
}

// ==================== SillyTavern Hooks ====================
/**
 * 在用户发送消息前调用
 * 使用SillyTavern的事件监听器系统
 */
async function onUserMessageSend(data) {
    try {
        // 获取或设置story_id
        if (!storyId) {
            // 尝试从当前聊天获取story_id
            // 可以从chat metadata或character card中获取
            if (typeof scriptAPI !== 'undefined' && scriptAPI.getChatMetadata) {
                const metadata = scriptAPI.getChatMetadata();
                storyId = metadata?.story_id || metadata?.chat_id || 'default_story';
            } else {
                storyId = 'default_story';
            }
        }
        
        // 获取状态
        const state = await fetchState(storyId);
        
        if (state) {
            // 生成状态摘要
            const summary = state_summary(state);
            
            // 注入到system prompt
            injectStatePanel(summary);
            
            // 更新侧栏
            updateSidebarPanel(state, null);
        }
    } catch (error) {
        console.error('[Memory Engine] 处理用户消息前钩子失败:', error);
    }
}

/**
 * 在模型生成assistant_draft后调用
 * 使用SillyTavern的事件监听器系统
 */
async function onAssistantDraftGenerated(data) {
    try {
        const draft = data.text || data.message || '';
        const userMessage = data.userMessage || data.user_message || '';
        
        if (!storyId) {
            if (typeof scriptAPI !== 'undefined' && scriptAPI.getChatMetadata) {
                const metadata = scriptAPI.getChatMetadata();
                storyId = metadata?.story_id || metadata?.chat_id || 'default_story';
            } else {
                storyId = 'default_story';
            }
        }
        
        // 调用后端处理
        const result = await processDraft(storyId, userMessage, draft);
        
        if (!result) {
            console.warn('[Memory Engine] 处理草稿返回空结果');
            return data; // 返回原始数据，继续处理
        }
        
        // 根据final_action处理
        if (result.final_action === 'PASS' || result.final_action === 'AUTO_FIX') {
            // 更新侧栏
            if (result.state && result.recent_events) {
                updateSidebarPanel(result.state, result.recent_events);
            }
            
            // 正常通过，返回原始数据
            return data;
            
        } else if (result.final_action === 'REWRITE') {
            // 需要重写，返回重写指令
            const rewriteInstructions = result.rewrite_instructions || '请根据一致性规则重写回复。';
            
            console.log('[Memory Engine] 需要重写:', rewriteInstructions);
            
            // 修改数据以包含重写指令
            // 使用SillyTavern的API来触发重写
            if (typeof scriptAPI !== 'undefined' && scriptAPI.modifyContext) {
                // 将重写指令添加到上下文
                scriptAPI.modifyContext({
                    system: `${scriptAPI.getSystemPrompt?.() || ''}\n\n[重写指令: ${rewriteInstructions}]`
                });
            }
            
            // 返回修改后的数据，触发重写
            return {
                ...data,
                text: null, // 清空文本，触发重新生成
                rewrite_instructions: rewriteInstructions,
                violations: result.violations || [],
            };
            
        } else if (result.final_action === 'ASK_USER') {
            // 需要用户澄清
            const questions = result.questions || ['需要您的澄清。'];
            
            console.log('[Memory Engine] 需要用户澄清:', questions);
            
            // 显示提示框
            if (typeof toastr !== 'undefined') {
                toastr.warning(questions.join('\n'), '需要澄清', { timeOut: 10000 });
            } else if (typeof alert !== 'undefined') {
                alert('需要澄清:\n' + questions.join('\n'));
            }
            
            // 阻止消息发送（返回null或空数据）
            return null;
        }
        
        return data;
        
    } catch (error) {
        console.error('[Memory Engine] 处理助手草稿钩子失败:', error);
        return data; // 出错时返回原始数据
    }
}

// ==================== 扩展设置UI ====================
/**
 * 创建扩展设置UI
 * 使用SillyTavern的扩展设置系统
 */
function createSettingsUI() {
    if (typeof extension_settings === 'undefined') {
        return; // SillyTavern的扩展设置系统不可用
    }
    
    if (!extension_settings.memory_engine) {
        extension_settings.memory_engine = {
            backend_url: DEFAULT_BACKEND_URL,
            story_id: null,
            enabled: true,
        };
    }
    
    // 从设置中读取配置
    backendUrl = extension_settings.memory_engine.backend_url || DEFAULT_BACKEND_URL;
    storyId = extension_settings.memory_engine.story_id || null;
    
    // 如果SillyTavern提供了扩展设置UI钩子，在这里注册
    if (typeof extension_prompt !== 'undefined') {
        // 使用SillyTavern的扩展设置系统
        extension_prompt.registerExtensionSettings('memory_engine', {
            title: 'Immersive Story Memory Engine',
            fields: [
                {
                    id: 'backend_url',
                    label: '后端URL',
                    type: 'text',
                    value: backendUrl,
                    placeholder: DEFAULT_BACKEND_URL,
                },
                {
                    id: 'story_id',
                    label: '故事ID',
                    type: 'text',
                    value: storyId || '',
                    placeholder: 'default_story',
                },
            ],
            onSave: (settings) => {
                extension_settings.memory_engine.backend_url = settings.backend_url || DEFAULT_BACKEND_URL;
                extension_settings.memory_engine.story_id = settings.story_id || null;
                backendUrl = extension_settings.memory_engine.backend_url;
                storyId = extension_settings.memory_engine.story_id;
                console.log('[Memory Engine] 设置已保存:', extension_settings.memory_engine);
            },
        });
    }
}

// ==================== 导出 ====================
// 根据SillyTavern的扩展系统，可能需要导出特定的函数
// 这里使用通用的导出方式

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        onExtensionLoad,
        onExtensionUnload,
        onUserMessageSend,
        onAssistantDraftGenerated,
        state_summary,
        fetchState,
        processDraft,
        updateSidebarPanel,
    };
}

// ==================== 扩展入口点 ====================
// SillyTavern扩展系统会自动调用这些函数

// 如果使用SillyTavern的标准扩展系统
if (typeof extension_settings !== 'undefined') {
    // 扩展设置初始化
    if (!extension_settings.memory_engine) {
        extension_settings.memory_engine = {
            backend_url: DEFAULT_BACKEND_URL,
            story_id: null,
            enabled: true,
        };
    }
    
    // 加载时初始化
    onExtensionLoad();
}

// 如果使用script标签直接加载
if (typeof window !== 'undefined') {
    // 等待DOM加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(onExtensionLoad, 500);
        });
    } else {
        setTimeout(onExtensionLoad, 500);
    }
    
    // 监听页面卸载
    window.addEventListener('beforeunload', onExtensionUnload);
}

