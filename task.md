# remove-changes-like

本项目已经实现去除changes包中的修订记录，例如使用以下命令即可去除修订记录。

```
uv run tex2ast remove-changes -i "F:\liuch586\repo\drfzh\paper-RISE-mixed-order\mixed\mixed.tex" -o "F:\liuch586\repo\drfzh\paper-RISE-mixed-order\mixed\mixed_clean.tex"
```

现在的需要在此基础上支持`.config\remove-changes.txt`中自定义的一些需要去掉的修订命令。
例如：去除cancel包的命令，sout命令，以及一些自定义的修订命令`\tG{new}`,`\sG{new}`默认支持以下命令：

`.config\remove-changes.txt`格式为：
```
# 带有old字样的内容将删除
\cancel{old}
\xcancel{old}
\sG{old}

# 带有new字样的内容将保留
\tG{new} # 保留new

# 可以组合old和new
\replaceG{new}{old}
```

可以通过`--changes-list=none`不读取默认的配置，通过`--changes-list=<path>`使用其他的changes配置。