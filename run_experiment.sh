export gpu=0
export config_json=configs/main.json5
host_name=$1
# 闲聊的匹配模型
echo "python train.py" "GPU:" ${gpu} "chat_corpus_log.txt"
CUDA_VISIBLE_DEVICES=${gpu} python train.py ${config_json} ${host_name}
#CUDA_VISIBLE_DEVICES=${gpu} nohup python -u train.py ${config_json} ${host_name} > chat_corpus_log.txt 2>&1 &
#tail -f chat_corpus_log.txt

## demo or test
#### python demo.py configs/main.json5  cloudminds  benchmark-0


# # 将模型对置信度保存到文件   目前只是针对训练集
#  python demo.py configs/main.json5  cloudminds  benchmark-1 train


