// ==UserScript==
// @name         NotebookLM Watermark Remover (Canvas Cover)
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Automatically covers the bottom-right watermark on NotebookLM images using the background color.
// @author       You
// @match        *://*/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // --- 配置参数 ---
    // 根据之前的 PRD，假设水印在右下角，且背景纯色
    const MASK_WIDTH = 115;  // 遮罩宽度 (px)
    const MASK_HEIGHT = 35;  // 遮罩高度 (px)
    
    // 自动检测的范围（从右下角向左/上偏移多少像素来取色）
    const COLOR_PICK_OFFSET_X = 5; 
    const COLOR_PICK_OFFSET_Y = 5;

    // 仅处理尺寸大于此值的图片，避免处理小图标
    const MIN_IMAGE_SIZE = 200;

    // 记录已处理过的图片 URL，防止重复处理
    const processedMap = new WeakSet();

    function processImage(img) {
        // 1. 检查是否需要处理
        if (processedMap.has(img)) return;
        if (img.width < MIN_IMAGE_SIZE || img.height < MIN_IMAGE_SIZE) return;
        
        // 简单的过滤逻辑：您可以根据 NotebookLM 图片的特征（如 src 或类名）进一步过滤
        // if (!img.src.includes('googleusercontent')) return; 

        // 标记为处理中，避免重复
        processedMap.add(img);

        // 2. 确保图片已加载
        if (!img.complete) {
            img.onload = () => processImage(img);
            return;
        }

        try {
            // 3. 创建 Canvas
            const canvas = document.createElement('canvas');
            canvas.width = img.naturalWidth || img.width;
            canvas.height = img.naturalHeight || img.height;
            const ctx = canvas.getContext('2d');

            // 绘制原图
            ctx.drawImage(img, 0, 0);

            // 4. 获取背景色 (自动取色策略)
            // 策略：取遮罩区域左侧的一个像素作为背景色
            const x0 = canvas.width - MASK_WIDTH;
            const y0 = canvas.height - MASK_HEIGHT;
            
            // 取样点坐标：遮罩左边一点，高度居中
            const sampleX = Math.max(0, x0 - COLOR_PICK_OFFSET_X);
            const sampleY = Math.min(canvas.height - 1, y0 + (MASK_HEIGHT / 2));
            
            const pixelData = ctx.getImageData(sampleX, sampleY, 1, 1).data;
            const bgColor = `rgb(${pixelData[0]}, ${pixelData[1]}, ${pixelData[2]})`;

            // 5. 绘制覆盖矩形
            ctx.fillStyle = bgColor;
            // 为了防止边缘溢出，可以稍微画大一点点，或者精确对齐
            ctx.fillRect(x0, y0, MASK_WIDTH, MASK_HEIGHT);

            // 6. 替换原图
            // 注意：跨域图片 (CORS) 可能会导致 toDataURL 失败 (Tainted Canvas)
            // 如果遇到跨域问题，需要在 img 标签上加 crossOrigin="anonymous" 
            // 但这通常需要服务器支持。如果是同源或支持 CORS 的 CDN (如 googleusercontent)，通常没问题。
            const newSrc = canvas.toDataURL('image/png');
            img.src = newSrc;
            
            console.log('[WatermarkRemover] Processed:', img);

        } catch (e) {
            console.warn('[WatermarkRemover] Failed to process image (likely CORS):', e);
        }
    }

    // --- 监听器设置 ---

    // 1. 处理页面上现有的图片
    function processAll() {
        document.querySelectorAll('img').forEach(processImage);
    }

    // 2. 监听动态加载的图片 (MutationObserver)
    const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.tagName === 'IMG') {
                    processImage(node);
                } else if (node.querySelectorAll) {
                    node.querySelectorAll('img').forEach(processImage);
                }
            });
        });
    });

    // 启动
    processAll();
    observer.observe(document.body, { childList: true, subtree: true });

    // 额外的定时检查，以防 Observer 漏掉（比如某些懒加载）
    setInterval(processAll, 2000);

})();
