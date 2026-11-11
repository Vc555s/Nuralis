# src/ai/llm_manager.py
import os
import torch
import threading
import time
import re
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from typing import Dict, List, Optional
from src.utils.logging_utils import logger
from pathlib import Path

class TimeoutError(Exception):
    pass

class ModelLoader:
    def __init__(self, config, model_name):
        self.config = config
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.error = None
        self.completed = False
    
    def load_model(self):
        try:
            # GGUF local model support via llama.cpp (llama-cpp-python)
            if isinstance(self.model_name, str) and self.model_name.lower().endswith(".gguf") and Path(self.model_name).exists():
                try:
                    from llama_cpp import Llama  # type: ignore
                except Exception as e:
                    raise RuntimeError(f"llama-cpp-python not installed or failed to import: {e}")
                # Initialize llama.cpp model with optimized settings
                ctx_len = int(self.config.get("models", {}).get("llm", {}).get("max_length", 2048))
                # Use all available CPU threads for faster loading
                n_threads = int(os.environ.get("LLAMA_CPP_THREADS", os.cpu_count() or 4))
                # Try to use GPU if available
                n_gpu_layers = int(os.environ.get("LLAMA_CPP_GPU_LAYERS", 0))
                
                logger.info(f"Loading GGUF model via llama.cpp: {self.model_name} (ctx={ctx_len}, threads={n_threads}, gpu_layers={n_gpu_layers})")
                self.model = Llama(
                    model_path=self.model_name,
                    n_ctx=ctx_len,
                    n_threads=n_threads,
                    n_gpu_layers=n_gpu_layers,
                    use_mmap=True,  # Memory mapping for faster loading
                    use_mlock=False,  # Don't lock memory (can cause issues)
                )
                self.tokenizer = None  # Not used for llama.cpp backend
                self.completed = True
                return

            # Configure quantization
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False
            )
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Set padding side to left for decoder-only models (GPT-J, GPT-2, etc.)
            # This is required for correct generation with decoder-only architectures
            self.tokenizer.padding_side = "left"
            
            # Add pad token if missing
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with proper configuration
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                quantization_config=quantization_config,
                trust_remote_code=True,
                torch_dtype=torch.float16,
                use_cache=True
            )
            
            self.completed = True
            
        except Exception as e:
            self.error = e
            self.completed = True

class LLMManager:
    def __init__(self, config: Dict):
        """Initialize LLM with proper quantization config and timeout handling"""
        self.config = config
        self.model_name = config["models"]["llm"]["name"]
        self.model = None  # HF model or llama.cpp Llama instance
        self.tokenizer = None  # HF tokenizer, not used for llama.cpp
        self.is_available_flag = False
        self.backend = "hf"  # or "llama_cpp"
        
        # Check if fallback is enabled
        enable_fallback = config.get("system", {}).get("enable_fallback", False)
        model_timeout = config.get("system", {}).get("model_timeout", 300)
        
        try:
            logger.info(f"Loading model {self.model_name}...")
            
            # Use threading-based timeout instead of signal
            loader = ModelLoader(config, self.model_name)
            thread = threading.Thread(target=loader.load_model)
            thread.daemon = True
            thread.start()
            
            # Wait for completion or timeout
            thread.join(timeout=model_timeout)
            
            if thread.is_alive():
                logger.error(f"❌ Model loading timed out after {model_timeout} seconds")
                if enable_fallback:
                    logger.info("🔄 Falling back to lightweight model...")
                    self._load_fallback_model()
                else:
                    raise TimeoutError("Model loading timed out")
            elif loader.error:
                logger.error(f"❌ Failed to load model: {str(loader.error)}")
                if enable_fallback:
                    logger.info("🔄 Falling back to lightweight model...")
                    self._load_fallback_model()
                else:
                    raise loader.error
            else:
                self.model = loader.model
                self.tokenizer = loader.tokenizer
                self.is_available_flag = True
                # Detect backend
                if self.tokenizer is None and self.model is not None and hasattr(self.model, "create_completion"):
                    self.backend = "llama_cpp"
                else:
                    self.backend = "hf"
                logger.info(f"✅ Successfully loaded {self.model_name} (backend={self.backend})")
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {str(e)}")
            if enable_fallback:
                logger.info("🔄 Falling back to lightweight model...")
                self._load_fallback_model()
            else:
                raise
    
    
    def _load_fallback_model(self):
        """Load a lightweight fallback model"""
        try:
            fallback_model = "microsoft/DialoGPT-medium"
            logger.info(f"Loading fallback model: {fallback_model}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.model = AutoModelForCausalLM.from_pretrained(
                fallback_model,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            
            self.is_available_flag = True
            logger.info("✅ Fallback model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Fallback model loading failed: {str(e)}")
            self.is_available_flag = False
    
    def is_available(self) -> bool:
        """Check if the model is available"""
        if not self.is_available_flag or self.model is None:
            return False
        if self.backend == "hf":
            return self.tokenizer is not None
        return True  # llama.cpp backend does not require tokenizer

    def _strict_research(self) -> bool:
        return bool(self.config.get("system", {}).get("strict_research_mode", True))

    def generate_text(self, prompt: str, max_new_tokens: int = 512) -> str:
        """Generate text with proper format handling for different models"""
        if not self.is_available():
            if self._strict_research():
                raise RuntimeError("LLM is not available (strict_research_mode)")
            return "Model not available for text generation."
        
        try:
            # llama.cpp GGUF backend
            if self.backend == "llama_cpp":
                try:
                    temperature = float(self.config["models"]["llm"].get("temperature", 0.7))
                    top_p = 0.9
                    # Use create_completion for simple prompt completion
                    out = self.model.create_completion(
                        prompt=prompt,
                        max_tokens=int(max_new_tokens),
                        temperature=temperature,
                        top_p=top_p,
                        stop=["</s>", "###", "User:", "System:", "Assistant:"],
                    )
                    response = out["choices"][0]["text"]
                except Exception as e:
                    logger.error(f"llama.cpp generation error: {e}")
                    if self._strict_research():
                        raise
                    response = ""
                
                # Post-process response similarly
                response = response.strip()
                # Aggressive cleanup using regex patterns below
                # fall through to cleanup pipeline
            else:
                # HF backend
                # Skip chat template for older Qwen models, but use it for Qwen2.5
                if "qwen2.5" in self.model_name.lower():
                    # Qwen2.5 models work well with chat templates
                    messages = [
                        {"role": "system", "content": "You are Nuralis Research Analyst, a helpful research assistant."},
                        {"role": "user", "content": prompt},
                    ]
                    try:
                        formatted_prompt = self.tokenizer.apply_chat_template(
                            messages, tokenize=False, add_generation_prompt=True
                        )
                    except Exception:
                        formatted_prompt = prompt
                elif "qwen" in self.model_name.lower():
                    # Older Qwen models - skip chat template
                    formatted_prompt = prompt
                elif hasattr(self.tokenizer, "apply_chat_template") and "dialogpt" not in self.model_name.lower():
                    messages = [
                        {"role": "system", "content": "You are Nuralis Research Analyst, a helpful research assistant."},
                        {"role": "user", "content": prompt},
                    ]
                    try:
                        formatted_prompt = self.tokenizer.apply_chat_template(
                            messages, tokenize=False, add_generation_prompt=True
                        )
                    except Exception:
                        formatted_prompt = prompt
                else:
                    formatted_prompt = prompt
                
                inputs = self.tokenizer(
                    formatted_prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self.config["models"]["llm"]["max_length"]
                ).to(self.model.device)
                
                # Safer generation parameters to avoid probability tensor errors
                generation_kwargs = {
                    **inputs,
                    "max_new_tokens": max_new_tokens,
                    "do_sample": True,
                    "top_p": 0.9,
                    "top_k": 50,
                    "repetition_penalty": 1.1,
                    "pad_token_id": self.tokenizer.pad_token_id,
                    "eos_token_id": self.tokenizer.eos_token_id,
                }
                
                # Add temperature only if it's reasonable
                temp = self.config["models"]["llm"]["temperature"]
                if 0.1 <= temp <= 2.0:
                    generation_kwargs["temperature"] = temp
                else:
                    generation_kwargs["temperature"] = 0.7
                
                # Add attention mask to avoid issues
                if "attention_mask" not in generation_kwargs:
                    generation_kwargs["attention_mask"] = inputs["attention_mask"]
                
                try:
                    outputs = self.model.generate(**generation_kwargs)
                except Exception as e:
                    logger.error(f"Generation error: {e}")
                    if self._strict_research():
                        raise
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=min(max_new_tokens, 200),
                        do_sample=False,  # Greedy decoding
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                    )
                
                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Clean up response - remove system prompt and instructions
            if self.backend == "hf" and hasattr(self.tokenizer, "chat_template") and "</s>" in response:
                response = response.split("</s>")[-1].strip()
            
            # Remove common system prompt patterns - more aggressive cleanup
            cleanup_patterns = [
                r"^system.*?user:",
                r"^System:.*?User:",
                r"^You are a.*?\.\s*",
                r"^As a.*?\.\s*",
                r"^Instructions:.*?\.\s*",
                r"^Write in.*?\.\s*",
                r"^Provide.*?using the dataset below\.\s*",
                r"^Dataset:.*?Instructions:",
                r"^Return only.*?\.\s*",
                r"^Format.*?\.\s*",
                r"^Length:.*?\.\s*",
                r"^Paragraph 1:.*?\.\s*",
                r"^Paragraph 2:.*?\.\s*",
                r"^Tone:.*?\.\s*",
                r"^Be specific.*?\.\s*",
                r"^Avoid.*?\.\s*",
                r"^Reference.*?\.\s*",
                r"^Analytical.*?\.\s*",
                r"^Decision-focused.*?\.\s*",
                r"^Executive Summary\s*:?\s*",
            ]
            
            for pattern in cleanup_patterns:
                response = re.sub(pattern, "", response, flags=re.DOTALL | re.IGNORECASE)
            
            # Additional cleanup for common patterns
            response = re.sub(r"^system\s+", "", response, flags=re.IGNORECASE)
            response = re.sub(r"^user\s+", "", response, flags=re.IGNORECASE)
            response = re.sub(r"^assistant\s+", "", response, flags=re.IGNORECASE)
            
            # More aggressive cleanup for Qwen model's chat template behavior
            # Remove everything before "assistant" or actual content
            if self.backend == "hf" and "assistant" in response.lower():
                response = response.split("assistant")[-1].strip()
            
            # Handle the specific pattern: "system You are a helpful research assistant. user System: ..."
            if self.backend == "hf" and "system You are a helpful research assistant. user System:" in response:
                response = response.split("system You are a helpful research assistant. user System:")[-1].strip()
            elif self.backend == "hf" and "system You are a helpful research assistant. user" in response:
                response = response.split("system You are a helpful research assistant. user")[-1].strip()
            
            # Remove everything before the first actual content (look for paragraph markers)
            if "###" in response:
                response = response.split("###")[-1].strip()
            elif "**" in response:
                # Find the first ** and start from there
                parts = response.split("**")
                if len(parts) > 1:
                    response = "**" + "**".join(parts[1:]).strip()
            
            # Remove any remaining "System:" or "User:" prefixes
            response = re.sub(r"^(System:|User:|Assistant:)\s*", "", response, flags=re.IGNORECASE)
            
            # Remove duplicate "Executive Summary" headers
            response = re.sub(r"^Executive Summary\s*\n\s*Executive Summary\s*\n?", "", response, flags=re.IGNORECASE)
            
            # Clean up extra whitespace and newlines
            response = re.sub(r'\n\s*\n', '\n\n', response.strip())
            
            # Additional cleanup for analyst-quality content
            # Remove exclamation marks and casual language
            response = re.sub(r'!+', '.', response)  # Replace multiple ! with single .
            response = re.sub(r'\s+', ' ', response)  # Normalize whitespace
            
            # Remove incomplete sentences at the end
            sentences = response.split('.')
            if len(sentences) > 1:
                # Check if last sentence is complete (has reasonable length)
                last_sentence = sentences[-1].strip()
                if len(last_sentence) < 10:  # Likely incomplete
                    response = '.'.join(sentences[:-1]) + '.'
            
            # Ensure proper sentence endings
            if response and not response.endswith(('.', '!', '?')):
                response += '.'
            
            return response if response else "No response generated."
            
        except Exception as e:
            logger.error(f"Generation error: {str(e)}")
            if self._strict_research():
                raise
            return f"Error generating response: {str(e)}"

    def generate_research_insights(self, papers_summary: str, query: str) -> str:
        """Generate research insights based on papers summary"""
        if not self.is_available():
            if self._strict_research():
                raise RuntimeError("LLM is not available (strict_research_mode)")
            return "AI insights are not available at the moment. Please try again later or check the system status."
        
        prompt = f"""You are Nuralis Research Analyst. Based on the following research papers summary, provide key insights about the current state and trends in the field.

Research Query: {query}
Papers Summary: {papers_summary}

Please provide:
1. Key findings and trends
2. Emerging patterns
3. Research gaps or opportunities
4. Future directions

Keep your analysis concise and focused on the most important insights."""
        
        return self.generate_text(prompt, max_new_tokens=400)

    def generate_followup_questions(self, papers_summary: str) -> List[str]:
        """Generate follow-up questions based on papers summary"""
        if not self.is_available():
            if self._strict_research():
                return []
            return [
                "What are the main limitations of current approaches?",
                "How can this research be applied in practice?",
                "What are the future research directions?"
            ]
        
        prompt = f"""Based on this research summary, generate 3-5 specific follow-up questions that would help dive deeper into the research area:

{papers_summary}

Format your response as a simple list, one question per line, without numbering or bullets. Focus on specific, actionable research questions."""
        
        response = self.generate_text(prompt, max_new_tokens=200)
        
        # Parse response into list of questions
        questions = []
        for line in response.split('\n'):
            line = line.strip()
            if line and '?' in line:
                # Remove any leading numbers or bullets
                line = line.lstrip('0123456789.- ')
                questions.append(line)
        
        if not questions:
            if self._strict_research():
                return []
            questions = [
                "What are the main limitations of current approaches?",
                "How can this research be applied in practice?",
                "What are the future research directions?"
            ]
        
        return questions[:5]  # Limit to 5 questions