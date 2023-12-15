import os
import torch
from llama import Llama
import fire
from gsmk_dataset import get_data_loader
import torch
import torch.nn.utils.prune as prune
    
backend = "qnnpack"

def print_model_size(mdl):
    torch.save(mdl.state_dict(), "tmp.pt")
    print("%.2f MB" %(os.path.getsize("tmp.pt")/1e6))
    os.remove('tmp.pt')



def get_model(ckpt_dir, tokenizer_path, max_seq_len, max_batch_size):
    generator = Llama.build(
        ckpt_dir=ckpt_dir,
        tokenizer_path=tokenizer_path,
        max_seq_len=max_seq_len,
        max_batch_size=max_batch_size,
    )
    return generator

def prune_model(llama):
    model = llama.model
    
    print(f'model type = {type(model)}')
    
    # set up pruning:
    for layer in model.layers: # each layer is a TransformerBlock
        # we only have nn.Parameter objects in RMSNorm class
        #import torch.nn.utils.prune as prune

        # Assuming you have a TransformerBlock object named 'layer'
        num_zeros = torch.sum(layer.weight == 0).item()
        total_params = layer.weight.numel()
        sparsity = num_zeros / total_params
        print(f"Sparsity of the TransformerBlock (before pruning): {sparsity}")
        model.layer = prune.random_unstructured(layer, name="attn_norm_w", amount=0.3) # name is a torch.nn.Parameter
        num_zeros = torch.sum(layer.weight == 0).item()
        sparsity = num_zeros / total_params
        print(f"Sparsity of the TransformerBlock (after pruning): {sparsity}")
        # prune.l1_unstructured(layer, name="bias", amount=3)
    
    
    """for i in range(len(model.layers)): # each layer is a TransformerBlock
        # we only have nn.Parameter objects in RMSNorm class
        model.layers[i] = prune.random_unstructured(model.layers[i], name="attn_norm_w", amount=0.3) # name is a torch.nn.Parameter
        # model.layer = prune.random_unstructured(layer, name="attn_norm_w", amount=0.3) # name is a torch.nn.Parameter
        # prune.l1_unstructured(layer, name="bias", amount=3)
    """
        
    
    
    #enc = model.encoder
    #dec = model.decoder
    
    # setup quantization
    """model.eval()
    model.qconfig = torch.ao.quantization.get_default_qconfig('x86')
    torch.backends.quantized.engine = backend
    torch.quantization.prepare(model, inplace=True)
    """
    
    # calibrate model to real world data
    dataloader = get_data_loader(3, 0)
    for _ in range(10):
        batch = next(iter(dataloader))
        llama.text_completion(
            batch,
            max_gen_len=512,
            temperature=0.6,
            top_p=0.9,
        )

    # convert in place
    # torch.quantization.convert(model, inplace=True)


def main():
    llama = get_model("/home/gyt2107/hpml_llama/llama-2-7b/", "tokenizer.model", 512, 6)
    print("model size before in-place pruning")
    print_model_size(llama.model)

    prune_model(llama)
    print("model size after in-place pruning")
    print_model_size(llama.model)

    # save the quantized model
    torch.save(llama.model.state_dict(), "quantized_model.pt")

if __name__ == "__main__":
    fire.Fire(main)