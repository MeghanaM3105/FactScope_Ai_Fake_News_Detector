
    (function() {
        // ========== DOM ELEMENTS ==========
        const pages = document.querySelectorAll('.page');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const newsInput = document.getElementById('newsInput');
        const backBtn = document.getElementById('backHomeBtn');
        const analyzeAnotherBtn = document.getElementById('analyzeAnother');
        const shareBtn = document.getElementById('shareResultBtn');
        const previewSpan = document.getElementById('previewText');
        const toast = document.getElementById('toast');
        const darkToggle = document.getElementById('darkToggle');
        
        // Result page elements
        const resultIcon = document.getElementById('resultIcon');
        const resultLabel = document.getElementById('resultLabel');
        const dynamicBadge = document.getElementById('dynamicBadge');
        const confidenceValue = document.getElementById('confidenceValue');
        const progressFill = document.getElementById('progressFill');
        const explainText = document.getElementById('explainText');
        const sentimentEl = document.getElementById('sentiment');
        const sentimentDetails = document.getElementById('sentimentDetails');
        const keywordsList = document.getElementById('keywordsList');
        const sentimentScore = document.getElementById('sentimentScore');

        // ========== API CONFIGURATION ==========
        const API_BASE_URL = 'http://localhost:5000/api';  // Change this to your backend URL

        // ========== HELPER FUNCTIONS ==========
        function showPage(pageId) {
            pages.forEach(p => p.classList.remove('active-page'));
            document.getElementById(pageId + 'Page').classList.add('active-page');
        }

        function showToast(msg, icon = 'info-circle', duration = 2500) {
            toast.style.display = 'flex';
            toast.querySelector('i').className = `fas fa-${icon}`;
            toast.querySelector('span').innerText = msg;
            setTimeout(() => toast.style.display = 'none', duration);
        }

        function setLoading(isLoading) {
            if (isLoading) {
                analyzeBtn.disabled = true;
                analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> Analyzing...';
            } else {
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyze Now';
            }
        }

        function updateResultUI(data) {
            const verdict = data.final_verdict;
            const ml = data.ml_prediction;
            const sentiment = data.sentiment_analysis;

            // Update preview
            previewSpan.innerText = data.input_text;

            // Update result header based on verdict
            if (verdict.is_fake) {
                resultIcon.innerHTML = '⚠️';
                resultLabel.innerText = 'FAKE NEWS DETECTED';
                dynamicBadge.innerHTML = 'FAKE';
                dynamicBadge.className = 'badge-fake';
                progressFill.className = 'progress-fill fill-red';
            } else {
                resultIcon.innerHTML = '✅';
                resultLabel.innerText = 'REAL NEWS VERIFIED';
                dynamicBadge.innerHTML = 'REAL';
                dynamicBadge.className = 'badge-real';
                progressFill.className = 'progress-fill fill-green';
            }

            // Update confidence
            confidenceValue.innerText = verdict.confidence + '%';
            progressFill.style.width = verdict.confidence + '%';
            explainText.innerText = verdict.explanation;

            // Update sentiment section
            sentimentEl.innerText = sentiment.sentiment;
            
            let sentimentDetailsText = '';
            if (verdict.is_fake) {
                sentimentDetailsText = '⚠️ Suspicious: ' + (sentiment.sensational_words?.length > 0 ? 
                    sentiment.sensational_words.slice(0,4).join(', ') : 'emotional tone detected');
            } else {
                sentimentDetailsText = '✅ Factual: ' + (sentiment.factual_words?.length > 0 ? 
                    sentiment.factual_words.slice(0,4).join(', ') : 'neutral reporting style');
            }
            sentimentDetails.innerText = sentimentDetailsText;
            
            const keywords = verdict.is_fake ? 
                (sentiment.sensational_words?.length > 0 ? sentiment.sensational_words.slice(0,5).join(', ') : 'sensational language') :
                (sentiment.factual_words?.length > 0 ? sentiment.factual_words.slice(0,5).join(', ') : 'factual terms');
            keywordsList.innerText = keywords;
            
            sentimentScore.innerText = sentiment.sentiment_score;

            // Add sources section if available
            const sourcesSection = document.getElementById('sources-section');
            if (sourcesSection) {
                sourcesSection.remove();
            }

            if (data.source_verification && (data.source_verification.trusted_sources?.length > 0 || 
                data.source_verification.fact_checks?.length > 0)) {
                
                let sourcesHtml = '<div id="sources-section" class="card mt-4"><h3>📰 Source Verification</h3>';
                
                if (data.source_verification.trusted_sources?.length > 0) {
                    sourcesHtml += '<h4>Trusted Sources:</h4>';
                    data.source_verification.trusted_sources.slice(0,3).forEach(s => {
                        sourcesHtml += `<p><a href="${s.url}" target="_blank" style="color: var(--primary);">🔗 ${s.title}</a><br><small>${s.source} • ${new Date(s.published).toLocaleDateString()}</small></p>`;
                    });
                }
                
                if (data.source_verification.fact_checks?.length > 0) {
                    sourcesHtml += '<h4 style="margin-top: 1rem;">Fact Checks:</h4>';
                    data.source_verification.fact_checks.slice(0,2).forEach(f => {
                        sourcesHtml += `<p><span style="font-weight: 600;">${f.rating || 'Unknown'}</span>: ${f.text}<br><small>by ${f.publisher || 'Unknown'}</small></p>`;
                    });
                }
                
                sourcesHtml += '</div>';
                
                const resultPage = document.getElementById('resultPage');
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = sourcesHtml;
                resultPage.insertBefore(tempDiv.firstChild, document.querySelector('.action-bar'));
            }
        }

        function fallbackShare(text) {
            navigator.clipboard?.writeText(text).then(() => {
                showToast('Result copied to clipboard!', 'clipboard');
            }).catch(() => {
                showToast('Press Ctrl+C to copy the result', 'info');
                console.log('Share text:', text);
            });
        }

        // ========== API CALLS ==========
        async function verifyNews(text) {
            const response = await fetch(`${API_BASE_URL}/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Analysis failed');
            }

            return await response.json();
        }

        async function checkHealth() {
            try {
                const response = await fetch(`${API_BASE_URL}/health`);
                return await response.json();
            } catch (error) {
                throw new Error('Backend server not reachable');
            }
        }

        // ========== EVENT HANDLERS ==========
        analyzeBtn.addEventListener('click', async () => {
            const inputText = newsInput.value.trim();
            
            if (!inputText) {
                showToast('Please enter news content to analyze', 'exclamation-triangle');
                newsInput.focus();
                return;
            }

            if (inputText.length < 10) {
                showToast('Please enter more text for accurate analysis', 'info');
                return;
            }

            setLoading(true);

            try {
                // First check if backend is healthy
                await checkHealth();
                
                // Perform verification
                const result = await verifyNews(inputText);
                
                if (result.success) {
                    updateResultUI(result);
                    showPage('result');
                    showToast('Analysis complete!', 'check-circle');
                } else {
                    throw new Error(result.error || 'Analysis failed');
                }
            } catch (error) {
                console.error('Analysis error:', error);
                
                if (error.message.includes('Backend server not reachable')) {
                    showToast('Cannot connect to server. Please ensure backend is running.', 'exclamation-triangle', 4000);
                } else {
                    showToast(error.message || 'Analysis failed. Please try again.', 'exclamation-triangle');
                }
            } finally {
                setLoading(false);
            }
        });

        // Navigation handlers
        backBtn.addEventListener('click', () => showPage('home'));
        analyzeAnotherBtn.addEventListener('click', () => {
            newsInput.value = '';
            newsInput.focus();
            showPage('home');
        });

        // Share handler
        shareBtn.addEventListener('click', async () => {
            const resultLabelText = resultLabel.innerText;
            const confidence = confidenceValue.innerText;
            const preview = previewSpan.innerText;
            const sentiment = sentimentEl.innerText;

            const shareText = `🔍 FactScope Analysis: ${resultLabelText} (${confidence} confidence)\n📊 Sentiment: ${sentiment}\n📰 Headline: ${preview}\n\nVerified with FactScope AI`;

            if (navigator.share) {
                try {
                    await navigator.share({
                        title: 'FactScope News Verification',
                        text: shareText,
                        url: window.location.href
                    });
                    showToast('Shared successfully!', 'check-circle');
                } catch (err) {
                    if (err.name !== 'AbortError') {
                        fallbackShare(shareText);
                    }
                }
            } else {
                fallbackShare(shareText);
            }
        });

        // Dark mode toggle
        darkToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark');
            const icon = darkToggle.querySelector('i');
            if (icon) {
                icon.className = document.body.classList.contains('dark') ? 'fas fa-sun' : 'fas fa-moon';
            }
        });

        // Enter key handler
        newsInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !analyzeBtn.disabled) {
                analyzeBtn.click();
            }
        });

        // ========== INITIALIZATION ==========
        async function initialize() {
            showPage('home');
            
            // Check backend connection on load
            try {
                const health = await checkHealth();
                console.log('✅ Backend connected:', health);
                showToast('Connected to FactScope server', 'check-circle', 2000);
            } catch (error) {
                console.warn('⚠️ Backend not connected:', error.message);
                showToast('Running in offline mode. Some features may be limited.', 'info', 4000);
            }

            // Add any additional initialization here
            const currentYear = new Date().getFullYear();
            const footerYear = document.querySelector('footer span:first-child');
            if (footerYear) {
                footerYear.innerHTML = `© ${currentYear} FactScope AI`;
            }
        }

        // Start the application
        initialize();
    })();
