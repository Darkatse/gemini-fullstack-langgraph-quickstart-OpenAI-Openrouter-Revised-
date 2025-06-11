import { useState, useEffect, useMemo } from "react";
import { Cpu, Loader2, AlertCircle, Info, Search, X } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface ModelInfo {
  id: string;
  name: string;
  description?: string;
  context_length?: number;
  pricing?: {
    prompt?: string;
    completion?: string;
  };
  architecture?: {
    input_modalities?: string[];
    output_modalities?: string[];
  };
}

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  className?: string;
  disabled?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onModelChange,
  className = "",
  disabled = false,
}) => {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchVisible, setIsSearchVisible] = useState(false);

  useEffect(() => {
    fetchModels();
  }, []);

  // Show search when there are more than 10 models
  useEffect(() => {
    setIsSearchVisible(models.length > 10);
  }, [models.length]);

  // Filter models based on search query
  const filteredModels = useMemo(() => {
    if (!searchQuery.trim()) {
      return models;
    }

    const query = searchQuery.toLowerCase().trim();
    return models.filter(model =>
      model.name.toLowerCase().includes(query) ||
      model.id.toLowerCase().includes(query) ||
      (model.description && model.description.toLowerCase().includes(query))
    );
  }, [models, searchQuery]);

  const fetchModels = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/models');
      if (!response.ok) {
        throw new Error(`Failed to fetch models: ${response.statusText}`);
      }
      
      const modelsData: ModelInfo[] = await response.json();
      setModels(modelsData);
      
      // Set default model if none selected and models are available
      if (!selectedModel && modelsData.length > 0) {
        // Try to find the current default model, otherwise use first available
        const defaultModel = modelsData.find(m => m.id === "deepseek/deepseek-r1-0528:free") || modelsData[0];
        onModelChange(defaultModel.id);
      }
    } catch (err) {
      console.error('Error fetching models:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch models');
      
      // Fallback to default models
      const fallbackModels: ModelInfo[] = [
        {
          id: "deepseek/deepseek-r1-0528:free",
          name: "DeepSeek R1 (Free)",
          description: "DeepSeek R1 model with free tier access",
          context_length: 128000
        },
        {
          id: "openai/gpt-4o-mini",
          name: "GPT-4o Mini",
          description: "OpenAI's efficient GPT-4o mini model",
          context_length: 128000
        }
      ];
      setModels(fallbackModels);
      
      if (!selectedModel) {
        onModelChange(fallbackModels[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  const selectedModelInfo = models.find(m => m.id === selectedModel);

  const clearSearch = () => {
    setSearchQuery("");
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Allow Escape key to clear search
    if (e.key === 'Escape') {
      clearSearch();
      e.preventDefault();
    }
  };

  const formatPrice = (price?: string) => {
    if (!price || price === "0") return "Free";
    const numPrice = parseFloat(price);
    if (numPrice < 0.000001) return "< $0.000001";
    return `$${numPrice.toFixed(6)}`;
  };

  const getModelDisplayName = (model: ModelInfo) => {
    // Truncate long names for better display
    if (model.name.length > 40) {
      return model.name.substring(0, 37) + "...";
    }
    return model.name;
  };

  if (loading) {
    return (
      <div className={`flex flex-row gap-2 bg-neutral-700 border-neutral-600 text-neutral-300 rounded-xl rounded-t-sm pl-2 ${className}`}>
        <div className="flex flex-row items-center text-sm">
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          Loading Models...
        </div>
      </div>
    );
  }

  if (error && models.length === 0) {
    return (
      <div className={`flex flex-row gap-2 bg-neutral-700 border-neutral-600 text-neutral-300 rounded-xl rounded-t-sm pl-2 ${className}`}>
        <div className="flex flex-row items-center text-sm">
          <AlertCircle className="h-4 w-4 mr-2 text-red-400" />
          <span className="text-red-400">Failed to load models</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchModels}
            className="ml-2 h-6 px-2 text-xs"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div className="flex flex-row gap-2 bg-neutral-700 border-neutral-600 text-neutral-300 focus:ring-neutral-500 rounded-xl rounded-t-sm pl-2">
        <div className="flex flex-row items-center text-sm">
          <Cpu className="h-4 w-4 mr-2" />
          Model
        </div>
        <Select value={selectedModel} onValueChange={onModelChange} disabled={disabled}>
          <SelectTrigger className="w-[200px] bg-transparent border-none cursor-pointer">
            <SelectValue placeholder="Select model">
              {selectedModelInfo ? getModelDisplayName(selectedModelInfo) : "Select model"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer max-h-[400px] overflow-y-auto">
            {/* Search input when there are many models */}
            {isSearchVisible && (
              <div className="sticky top-0 z-10 p-2 bg-neutral-700 border-b border-neutral-600">
                <div className="relative">
                  <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-neutral-400" />
                  <Input
                    type="text"
                    placeholder={`Search ${models.length} models...`}
                    value={searchQuery}
                    onChange={handleSearchChange}
                    onKeyDown={handleSearchKeyDown}
                    className="pl-8 pr-8 bg-neutral-800 border-neutral-600 text-neutral-300 placeholder-neutral-400 focus:ring-neutral-500 focus:border-neutral-500"
                  />
                  {searchQuery && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearSearch}
                      className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0 hover:bg-neutral-600"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
                {searchQuery && (
                  <div className="text-xs text-neutral-400 mt-1 px-1">
                    {filteredModels.length} of {models.length} models
                  </div>
                )}
              </div>
            )}

            {/* Model list */}
            {filteredModels.length === 0 ? (
              <div className="p-4 text-center text-neutral-400 text-sm">
                {searchQuery ? "No models found matching your search" : "No models available"}
              </div>
            ) : (
              filteredModels.map((model) => (
                <SelectItem
                  key={model.id}
                  value={model.id}
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  <div className="flex flex-col">
                    <span className="font-medium">{getModelDisplayName(model)}</span>
                    {model.pricing && (
                      <span className="text-xs text-neutral-400">
                        Input: {formatPrice(model.pricing.prompt)}/token •
                        Output: {formatPrice(model.pricing.completion)}/token
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>

        {selectedModelInfo && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
            className="h-8 w-8 p-0 hover:bg-neutral-600"
          >
            <Info className="h-4 w-4" />
          </Button>
        )}
      </div>
      
      {error && (
        <div className="text-xs text-yellow-400 px-2">
          Warning: Using fallback models due to API error
        </div>
      )}
      
      {showDetails && selectedModelInfo && (
        <div className="bg-neutral-800 border border-neutral-600 rounded-lg p-3 text-sm">
          <div className="font-medium text-neutral-200 mb-2">{selectedModelInfo.name}</div>
          {selectedModelInfo.description && (
            <div className="text-neutral-400 mb-2 text-xs">{selectedModelInfo.description}</div>
          )}
          <div className="grid grid-cols-2 gap-2 text-xs">
            {selectedModelInfo.context_length && (
              <div>
                <span className="text-neutral-500">Context:</span>
                <span className="text-neutral-300 ml-1">{selectedModelInfo.context_length.toLocaleString()} tokens</span>
              </div>
            )}
            {selectedModelInfo.pricing && (
              <div>
                <span className="text-neutral-500">Pricing:</span>
                <span className="text-neutral-300 ml-1">
                  {formatPrice(selectedModelInfo.pricing.prompt)}/token
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
